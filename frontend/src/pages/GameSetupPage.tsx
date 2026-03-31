import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function GameSetupPage() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<any[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [config, setConfig] = useState({ small_blind: 50, big_blind: 100, buy_in: 5000, num_hands: 10 });
  const [unlimited, setUnlimited] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.listAgents().then(setAgents).catch(() => {}); }, []);

  const toggleAgent = (id: string) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleStart = async () => {
    if (selected.length < 2) { alert('Select at least 2 agents'); return; }
    setLoading(true);
    try {
      const numHands = unlimited ? 999999 : config.num_hands;
      const { session_id } = await api.createGame({ agent_ids: selected, ...config });
      await api.startGame(session_id, numHands);
      navigate(`/games/${session_id}`);
    } catch (e: any) { alert(e.message); }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="page-title">New Game</h1>

      <div className="card">
        <h2>Game Settings</h2>
        <div className="grid-4">
          <div>
            <label>Small Blind</label>
            <input type="number" value={config.small_blind} onChange={e => setConfig({...config, small_blind: +e.target.value})} />
          </div>
          <div>
            <label>Big Blind</label>
            <input type="number" value={config.big_blind} onChange={e => setConfig({...config, big_blind: +e.target.value})} />
          </div>
          <div>
            <label>Buy-in</label>
            <input type="number" value={config.buy_in} onChange={e => setConfig({...config, buy_in: +e.target.value})} />
          </div>
          <div>
            <label>Number of Hands</label>
            <div style={{display: 'flex', alignItems: 'center', gap: 8, marginTop: 4}}>
              <label style={{display: 'flex', alignItems: 'center', gap: 4, margin: 0, cursor: 'pointer'}}>
                <input type="radio" checked={!unlimited} onChange={() => setUnlimited(false)} />
                <span>Set:</span>
              </label>
              <input
                type="number"
                value={config.num_hands}
                onChange={e => setConfig({...config, num_hands: +e.target.value})}
                disabled={unlimited}
                style={{width: 80, opacity: unlimited ? 0.4 : 1}}
              />
              <label style={{display: 'flex', alignItems: 'center', gap: 4, margin: 0, cursor: 'pointer'}}>
                <input type="radio" checked={unlimited} onChange={() => setUnlimited(true)} />
                <span>Unlimited</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Select Agents ({selected.length} selected)</h2>
        {agents.length === 0 ? (
          <p className="empty-state">No agents available. <a href="/agents" style={{color:'#22d3ee'}}>Create agents first</a>.</p>
        ) : (
          <div style={{display:'flex', flexWrap:'wrap', gap:10}}>
            {agents.map(a => (
              <div key={a.agent_id}
                onClick={() => toggleAgent(a.agent_id)}
                style={{
                  padding: '12px 20px', borderRadius: 10, cursor: 'pointer',
                  border: selected.includes(a.agent_id) ? '2px solid #0ea5e9' : '2px solid #334155',
                  background: selected.includes(a.agent_id) ? '#0ea5e922' : '#1e293b',
                }}>
                <div style={{fontWeight:600}}>{a.display_name}</div>
                <div style={{fontSize:'0.8rem',color:'#94a3b8'}}>{a.skill_level} / {a.play_style.toUpperCase()}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="btn btn-primary" onClick={handleStart} disabled={loading || selected.length < 2}
        style={{fontSize:'1rem', padding:'12px 32px'}}>
        {loading ? 'Starting...' : `Start Game (${selected.length} players)`}
      </button>
    </div>
  );
}
