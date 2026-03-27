import { useEffect, useState } from 'react';
import { api } from '../api/client';

const STYLES = ['tag', 'lag', 'calling_station', 'rock', 'fish', 'maniac'];
const SKILLS = ['novice', 'intermediate', 'expert'];

export default function AgentManagePage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [form, setForm] = useState({ display_name: '', skill_level: 'expert', play_style: 'tag', custom_traits: '' });
  const [loading, setLoading] = useState(false);

  const refresh = () => api.listAgents().then(setAgents).catch(() => {});
  useEffect(() => { refresh(); }, []);

  const handleCreate = async () => {
    if (!form.display_name.trim()) return;
    setLoading(true);
    try {
      await api.createAgent(form);
      setForm({ display_name: '', skill_level: 'expert', play_style: 'tag', custom_traits: '' });
      refresh();
    } catch (e: any) { alert(e.message); }
    setLoading(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this agent?')) return;
    await api.deleteAgent(id);
    refresh();
  };

  return (
    <div>
      <h1 className="page-title">Agent Management</h1>

      <div className="card">
        <h2>Create New Agent</h2>
        <div className="grid-2">
          <div>
            <label>Name</label>
            <input value={form.display_name} onChange={e => setForm({...form, display_name: e.target.value})} placeholder="e.g. Alice" />
          </div>
          <div>
            <label>Custom Traits</label>
            <input value={form.custom_traits} onChange={e => setForm({...form, custom_traits: e.target.value})} placeholder="Optional description" />
          </div>
          <div>
            <label>Skill Level</label>
            <select value={form.skill_level} onChange={e => setForm({...form, skill_level: e.target.value})}>
              {SKILLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label>Play Style</label>
            <select value={form.play_style} onChange={e => setForm({...form, play_style: e.target.value})}>
              {STYLES.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-12">
          <button className="btn btn-primary" onClick={handleCreate} disabled={loading}>
            {loading ? 'Creating...' : 'Create Agent'}
          </button>
        </div>
      </div>

      <div className="card">
        <h2>All Agents ({agents.length})</h2>
        {agents.length === 0 ? (
          <p className="empty-state">No agents created yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Name</th><th>Skill</th><th>Style</th><th>Provider</th><th>Hands</th><th>Profit</th><th></th></tr>
            </thead>
            <tbody>
              {agents.map(a => (
                <tr key={a.agent_id}>
                  <td><strong>{a.display_name}</strong><br/><span style={{fontSize:'0.75rem',color:'#64748b'}}>{a.agent_id}</span></td>
                  <td><span className={`tag tag-${a.skill_level}`}>{a.skill_level}</span></td>
                  <td>{a.play_style.toUpperCase()}</td>
                  <td>{a.llm_provider}</td>
                  <td>{a.total_hands}</td>
                  <td className={a.total_profit >= 0 ? 'text-green' : 'text-red'}>{a.total_profit}</td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => handleDelete(a.agent_id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
