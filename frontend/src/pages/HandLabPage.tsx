import { useEffect, useState, useRef, useCallback } from 'react';
import { api } from '../api/client';
import CardPicker from '../components/CardPicker';

function CardView({ card }: { card: string }) {
  if (!card) return <div className="playing-card facedown">?</div>;
  const suit = card[1];
  const isRed = suit === 'h' || suit === 'd';
  const suitSymbol: Record<string, string> = { h: '\u2665', d: '\u2666', c: '\u2663', s: '\u2660' };
  return <div className={`playing-card ${isRed ? 'red' : ''}`}>{card[0]}{suitSymbol[suit] || suit}</div>;
}

function ActionBadge({ action }: { action: string }) {
  const cls: Record<string, string> = { fold: 'badge-fold', call: 'badge-call', raise: 'badge-raise', check: 'badge-check', all_in: 'badge-allin' };
  return <span className={`badge ${cls[action] || ''}`}>{action}</span>;
}

function EquityBar({ winPct, label }: { winPct: number; label: string }) {
  const color = winPct > 60 ? '#22c55e' : winPct > 30 ? '#eab308' : winPct > 0 ? '#f87171' : '#334155';
  return (
    <div style={{ marginTop: 4 }}>
      <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: 2 }}>{label}: {winPct}%</div>
      <div style={{ background: '#334155', borderRadius: 4, height: 6, width: 100 }}>
        <div style={{
          background: color, borderRadius: 4, height: 6,
          width: `${winPct}%`, transition: 'width 0.5s ease, background 0.5s ease',
        }} />
      </div>
    </div>
  );
}

interface PlayerConfig {
  agent_id: string;
  chips: number;
  hole_cards: string[];
}

const SPEEDS = [
  { label: 'Fast', ms: 200 },
  { label: 'Normal', ms: 600 },
  { label: 'Slow', ms: 1200 },
];

export default function HandLabPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [players, setPlayers] = useState<PlayerConfig[]>([
    { agent_id: '', chips: 5000, hole_cards: [] },
    { agent_id: '', chips: 5000, hole_cards: [] },
  ]);
  const [communityCards, setCommunityCards] = useState<string[]>([]);
  const [smallBlind, setSmallBlind] = useState(50);
  const [bigBlind, setBigBlind] = useState(100);
  const [runCount, setRunCount] = useState(10);
  const [speedIdx, setSpeedIdx] = useState(1); // Normal
  const [loading, setLoading] = useState(false);

  // Results
  const [allResults, setAllResults] = useState<any[]>([]);
  const [selectedRunIdx, setSelectedRunIdx] = useState(0);
  const [multiSummary, setMultiSummary] = useState<any>(null);

  // Step playback
  const [currentStep, setCurrentStep] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<any>(null);

  useEffect(() => { api.listAgents().then(setAgents).catch(() => {}); }, []);

  const selectedResult = allResults[selectedRunIdx] || null;
  const steps: any[] = selectedResult?.steps || [];
  const totalSteps = steps.length;

  // Derive display state from steps up to currentStep
  const displayState = useCallback(() => {
    if (!steps.length || currentStep < 0) {
      return { community: [], pot: 0, equity: [], actions: [], playerCards: {}, winners: null, chipChanges: null };
    }
    let community: string[] = [];
    let pot = 0;
    let equity: any[] = [];
    const actions: any[] = [];
    let playerCards: Record<string, any> = {};
    let winners: any = null;
    let chipChanges: any = null;

    for (let i = 0; i <= Math.min(currentStep, steps.length - 1); i++) {
      const s = steps[i];
      if (s.type === 'hand_start') {
        community = s.community_cards || [];
        pot = s.pot || 0;
        equity = s.equity || [];
        playerCards = s.players || {};
      } else if (s.type === 'street') {
        community = s.community_cards || [];
        pot = s.pot || 0;
        equity = s.equity || [];
      } else if (s.type === 'action') {
        pot = s.pot_after || pot;
        actions.push(s);
      } else if (s.type === 'result') {
        community = s.community_cards || [];
        pot = s.pot || pot;
        equity = s.equity || [];
        winners = s.winners;
        chipChanges = s.chip_changes;
      }
    }
    return { community, pot, equity, actions, playerCards, winners, chipChanges };
  }, [steps, currentStep]);

  const state = displayState();

  // Auto-play timer
  useEffect(() => {
    if (playing && currentStep < totalSteps - 1) {
      timerRef.current = setTimeout(() => {
        setCurrentStep(prev => prev + 1);
      }, SPEEDS[speedIdx].ms);
      return () => clearTimeout(timerRef.current);
    } else if (currentStep >= totalSteps - 1) {
      setPlaying(false);
    }
  }, [playing, currentStep, totalSteps, speedIdx]);

  // Start playback when new result loads
  useEffect(() => {
    if (steps.length > 0) {
      setCurrentStep(0);
      setPlaying(true);
    }
  }, [selectedRunIdx, allResults]);

  const allUsedCards = [...communityCards, ...players.flatMap(p => p.hole_cards)];

  const updatePlayer = (idx: number, update: Partial<PlayerConfig>) => {
    setPlayers(prev => prev.map((p, i) => i === idx ? { ...p, ...update } : p));
  };
  const addPlayer = () => { if (players.length < 6) setPlayers(prev => [...prev, { agent_id: '', chips: 5000, hole_cards: [] }]); };
  const removePlayer = (idx: number) => { if (players.length > 2) setPlayers(prev => prev.filter((_, i) => i !== idx)); };
  const canRun = players.every(p => p.agent_id) && players.length >= 2;

  const buildScenario = () => ({
    players: players.map((p, i) => ({ agent_id: p.agent_id, chips: p.chips, hole_cards: p.hole_cards, seat_index: i })),
    community_cards: communityCards, small_blind: smallBlind, big_blind: bigBlind, dealer_index: 0,
  });

  const handleRunOnce = async () => {
    setLoading(true); setAllResults([]); setMultiSummary(null); setSelectedRunIdx(0); setCurrentStep(-1); setPlaying(false);
    try {
      const r = await api.runLabOnce(buildScenario());
      setAllResults([r]);
    } catch (e: any) { alert(e.message); }
    setLoading(false);
  };

  const handleRunMultiple = async () => {
    setLoading(true); setAllResults([]); setMultiSummary(null); setSelectedRunIdx(0); setCurrentStep(-1); setPlaying(false);
    try {
      const r = await api.runLabMultiple({ scenario: buildScenario(), count: runCount });
      setAllResults(r.results || []);
      setMultiSummary(r.summary || null);
    } catch (e: any) { alert(e.message); }
    setLoading(false);
  };

  // Playback controls
  const goTo = (step: number) => { setPlaying(false); setCurrentStep(Math.max(-1, Math.min(step, totalSteps - 1))); };
  const togglePlay = () => {
    if (currentStep >= totalSteps - 1) { setCurrentStep(0); setPlaying(true); }
    else setPlaying(!playing);
  };

  // Get player equity by display name
  const getEquity = (name: string) => {
    const eq = state.equity.find((e: any) => e.player_id === name);
    return eq ? eq.win_pct : null;
  };

  return (
    <div>
      <h1 className="page-title">Hand Lab</h1>

      {/* Scenario Setup */}
      <div className="card">
        <h2>Scenario Setup</h2>
        {players.map((p, idx) => (
          <div key={idx} style={{
            display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 12,
            padding: 12, background: '#0f172a', borderRadius: 8,
          }}>
            <div style={{ minWidth: 60 }}>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Player {idx + 1}</label>
              <select value={p.agent_id} onChange={e => updatePlayer(idx, { agent_id: e.target.value })}
                style={{ width: '100%', marginTop: 4 }}>
                <option value="">Select agent</option>
                {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.display_name}</option>)}
              </select>
            </div>
            <div style={{ minWidth: 80 }}>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Chips</label>
              <input type="number" value={p.chips} onChange={e => updatePlayer(idx, { chips: +e.target.value })}
                style={{ width: 80, marginTop: 4 }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Hole Cards</label>
              <CardPicker selectedCards={p.hole_cards} maxCards={2} usedCards={allUsedCards}
                onChange={cards => updatePlayer(idx, { hole_cards: cards })} />
            </div>
            {players.length > 2 && (
              <button onClick={() => removePlayer(idx)}
                style={{ padding: '4px 8px', color: '#f87171', background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.1rem' }}>x</button>
            )}
          </div>
        ))}
        {players.length < 6 && <button className="btn btn-sm" onClick={addPlayer} style={{ marginBottom: 12 }}>+ Add Player</button>}

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Community Cards (optional, 0-5)</label>
          <CardPicker selectedCards={communityCards} maxCards={5} usedCards={allUsedCards} onChange={setCommunityCards} />
        </div>

        <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Small Blind</label>
            <input type="number" value={smallBlind} onChange={e => setSmallBlind(+e.target.value)} style={{ width: 80 }} />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Big Blind</label>
            <input type="number" value={bigBlind} onChange={e => setBigBlind(+e.target.value)} style={{ width: 80 }} />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Playback Speed</label>
            <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
              {SPEEDS.map((s, i) => (
                <button key={s.label} className={`btn btn-sm ${i === speedIdx ? 'btn-primary' : ''}`}
                  onClick={() => setSpeedIdx(i)} style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button className="btn btn-primary" onClick={handleRunOnce} disabled={!canRun || loading}>
            {loading ? 'Running...' : 'Run Once'}
          </button>
          <button className="btn btn-primary" onClick={handleRunMultiple} disabled={!canRun || loading}
            style={{ background: '#7c3aed' }}>
            Run {runCount} Times
          </button>
          <input type="number" value={runCount} onChange={e => setRunCount(+e.target.value)} min={2} max={100} style={{ width: 60 }} />
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>times</span>
        </div>
      </div>

      {/* Live Table + Playback */}
      {selectedResult && (
        <>
          <div className="card">
            <h2>
              {allResults.length > 1 ? `Run #${selectedRunIdx + 1}` : 'Result'}
              {currentStep >= 0 && currentStep < totalSteps - 1 && (
                <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginLeft: 8 }}>
                  {steps[currentStep]?.street || steps[currentStep]?.type || ''}
                </span>
              )}
            </h2>

            {/* Poker Table */}
            <div className="poker-table" style={{ marginBottom: 16 }}>
              <div className="pot-display">Pot: {state.pot}</div>
              <div className="community-cards">
                {state.community.length > 0
                  ? state.community.map((c: string, i: number) => <CardView key={i} card={c} />)
                  : [1, 2, 3, 4, 5].map(i => <CardView key={i} card="" />)
                }
              </div>
            </div>

            {/* Player Seats with Equity */}
            <div className="seats-container" style={{ marginBottom: 16 }}>
              {Object.entries(selectedResult.player_cards || {}).map(([pid, cards]: [string, any]) => {
                const eq = getEquity(pid);
                const isFolded = state.actions.some((a: any) => a.player_id === pid && a.action === 'fold');
                const isWinner = state.winners && state.winners[pid];
                const chipChange = state.chipChanges?.[pid];
                return (
                  <div key={pid} className={`seat ${isFolded ? 'seat-folded' : ''}`}
                    style={isWinner ? { border: '2px solid #22c55e' } : {}}>
                    <div className="name">{pid}</div>
                    <div className="hole-cards">
                      {cards.map((c: string, i: number) => <CardView key={i} card={c} />)}
                    </div>
                    {eq != null && <EquityBar winPct={eq} label="Win" />}
                    <div className="chips">{selectedResult.final_chips?.[pid]} chips</div>
                    {chipChange != null && chipChange !== 0 && state.chipChanges && (
                      <div className={chipChange > 0 ? 'chip-change-positive' : 'chip-change-negative'}>
                        {chipChange > 0 ? `+${chipChange}` : chipChange}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Playback Controls */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
              background: '#0f172a', borderRadius: 8, marginBottom: 16,
            }}>
              <button className="btn btn-sm" onClick={() => goTo(0)} title="Start">{'|<'}</button>
              <button className="btn btn-sm" onClick={() => goTo(currentStep - 1)} title="Previous">{'<'}</button>
              <button className="btn btn-sm btn-primary" onClick={togglePlay} style={{ minWidth: 60 }}>
                {playing ? 'Pause' : currentStep >= totalSteps - 1 ? 'Replay' : 'Play'}
              </button>
              <button className="btn btn-sm" onClick={() => goTo(currentStep + 1)} title="Next">{'>'}</button>
              <button className="btn btn-sm" onClick={() => goTo(totalSteps - 1)} title="End">{'>|'}</button>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginLeft: 8 }}>
                Step {Math.max(0, currentStep + 1)} / {totalSteps}
              </span>
              {/* Progress bar */}
              <div style={{ flex: 1, background: '#334155', borderRadius: 4, height: 6, cursor: 'pointer', marginLeft: 8 }}
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const pct = (e.clientX - rect.left) / rect.width;
                  goTo(Math.round(pct * (totalSteps - 1)));
                }}>
                <div style={{
                  background: '#0ea5e9', borderRadius: 4, height: 6,
                  width: `${totalSteps > 1 ? ((currentStep + 1) / totalSteps) * 100 : 0}%`,
                  transition: 'width 0.2s',
                }} />
              </div>
            </div>

            {/* Action Timeline (up to current step) */}
            {state.actions.length > 0 && (
              <div className="timeline" style={{ maxHeight: 250, overflowY: 'auto' }}>
                {state.actions.map((a: any, i: number) => (
                  <div key={i}>
                    <div className="timeline-item">
                      <span style={{ width: 70, color: '#64748b', fontWeight: 600 }}>{a.street}</span>
                      <span style={{ width: 90 }}>{a.player_id}</span>
                      <ActionBadge action={a.action} />
                      {a.amount > 0 && <span className="text-yellow" style={{ marginLeft: 4 }}>{a.amount}</span>}
                      {a.round_bet > 0 && (
                        <span style={{ marginLeft: 8, fontSize: '0.75rem', color: '#94a3b8' }}>Round: {a.round_bet}</span>
                      )}
                      <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#64748b' }}>Pot: {a.pot_after}</span>
                    </div>
                    {a.thinking && <div className="thinking-panel">{a.thinking}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Multi-Run Summary + Run Selector */}
          {multiSummary && (
            <div className="card">
              <h2>Summary ({multiSummary.total_runs} runs)</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
                {Object.entries(multiSummary.win_rate || {}).map(([name, rate]: [string, any]) => (
                  <div key={name} style={{ background: '#0f172a', padding: 16, borderRadius: 8 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>{name}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ color: '#94a3b8' }}>Win Rate</span>
                      <span className="text-green">{rate}%</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ color: '#94a3b8' }}>Avg Profit</span>
                      <span className={multiSummary.avg_profit[name] >= 0 ? 'text-green' : 'text-red'}>
                        {multiSummary.avg_profit[name] >= 0 ? '+' : ''}{multiSummary.avg_profit[name]}
                      </span>
                    </div>
                    <div style={{ background: '#334155', borderRadius: 4, height: 8, marginTop: 8 }}>
                      <div style={{ background: '#22c55e', borderRadius: 4, height: 8, width: `${rate}%`, transition: 'width 0.3s' }} />
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: 12 }}>
                Average Pot: {multiSummary.avg_pot}
              </div>

              {/* Run Selector */}
              <h3 style={{ fontSize: '0.9rem', marginBottom: 8 }}>Select Run</h3>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {allResults.map((r, i) => {
                  const isWin = Object.keys(r.winners || {}).length > 0;
                  return (
                    <button key={i}
                      className={`btn btn-sm ${i === selectedRunIdx ? 'btn-primary' : ''}`}
                      onClick={() => { setSelectedRunIdx(i); setCurrentStep(-1); setPlaying(false); }}
                      style={{
                        padding: '4px 10px', fontSize: '0.75rem',
                        minWidth: 44,
                        border: i === selectedRunIdx ? '2px solid #0ea5e9' : '1px solid #334155',
                      }}>
                      #{i + 1}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
