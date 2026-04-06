import { useEffect, useState, useRef, useCallback } from 'react';
import { api, createGameWS } from '../api/client';
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

type LabPhase = 'setup' | 'live' | 'finished';

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
  const [loading, setLoading] = useState(false);

  // State machine
  const [phase, setPhase] = useState<LabPhase>('setup');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Live state (during WebSocket streaming)
  const [liveActions, setLiveActions] = useState<any[]>([]);
  const [liveCommunity, setLiveCommunity] = useState<string[]>([]);
  const [livePot, setLivePot] = useState(0);
  const [liveEquity, setLiveEquity] = useState<any[]>([]);
  const [livePlayerCards, setLivePlayerCards] = useState<Record<string, any>>({});
  const [thinkingPlayer, setThinkingPlayer] = useState<string | null>(null);
  const [handInProgress, setHandInProgress] = useState(false);
  const [currentHandNum, setCurrentHandNum] = useState(0);
  const [totalHands, setTotalHands] = useState(1);

  // Completed hands + summary
  const [completedHands, setCompletedHands] = useState<any[]>([]);
  const [multiSummary, setMultiSummary] = useState<any>(null);
  const [selectedHandIdx, setSelectedHandIdx] = useState<number | null>(null);

  const liveLogRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.listAgents().then(setAgents).catch(() => {}); }, []);

  // Auto-scroll live log
  useEffect(() => {
    if (liveLogRef.current) {
      liveLogRef.current.scrollTop = liveLogRef.current.scrollHeight;
    }
  }, [liveActions]);

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

  const cleanupWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const handleStart = async (count: number) => {
    setLoading(true);
    setCompletedHands([]);
    setMultiSummary(null);
    setSelectedHandIdx(null);
    setCurrentHandNum(0);
    setTotalHands(count);

    try {
      const { session_id } = await api.startLab({ scenario: buildScenario(), count });
      setSessionId(session_id);
      setPhase('live');

      // Connect WebSocket
      const ws = createGameWS(session_id);
      wsRef.current = ws;

      ws.onopen = () => { console.log('[Lab WS] connected'); };
      ws.onclose = () => { console.log('[Lab WS] disconnected'); };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        console.log('[Lab WS] event:', msg.type);

        if (msg.type === 'hand_start') {
          setHandInProgress(true);
          setCurrentHandNum(prev => prev + 1);
          const playerCards: Record<string, any> = {};
          const playersData = msg.data.players || {};
          for (const [name, info] of Object.entries(playersData) as [string, any][]) {
            playerCards[name] = { hole_cards: info.hole_cards || [], chips: info.chips };
          }
          setLivePlayerCards(playerCards);
          setLivePot(msg.data.pot || 0);
          setLiveActions([]);
          setLiveCommunity([]);
          setThinkingPlayer(null);
          setLiveEquity(msg.data.equity || []);

        } else if (msg.type === 'street_start') {
          setLiveCommunity(msg.data.community_cards || []);
          setLivePot(msg.data.pot || 0);
          setThinkingPlayer(null);
          if (msg.data.equity) setLiveEquity(msg.data.equity);

        } else if (msg.type === 'player_thinking') {
          setThinkingPlayer(msg.data.player_id);

        } else if (msg.type === 'player_action') {
          setThinkingPlayer(null);
          setLivePot(msg.data.pot_after || 0);
          setLiveActions(prev => [...prev, msg.data]);

        } else if (msg.type === 'hand_complete') {
          setHandInProgress(false);
          setThinkingPlayer(null);
          setCompletedHands(prev => [...prev, msg.data]);

        } else if (msg.type === 'lab_finished') {
          setPhase('finished');
          if (msg.data.summary) setMultiSummary(msg.data.summary);
          setHandInProgress(false);
          setThinkingPlayer(null);
          cleanupWs();
        }
      };
    } catch (e: any) {
      alert(e.message);
      setPhase('setup');
    }
    setLoading(false);
  };

  const handleStop = () => {
    if (sessionId) {
      api.stopGame(sessionId).catch(() => {});
    }
  };

  const handleBackToSetup = () => {
    cleanupWs();
    setPhase('setup');
    setSessionId(null);
    setCompletedHands([]);
    setMultiSummary(null);
    setSelectedHandIdx(null);
    setLiveActions([]);
    setLiveCommunity([]);
    setLivePot(0);
    setLiveEquity([]);
    setLivePlayerCards({});
    setThinkingPlayer(null);
    setHandInProgress(false);
    setCurrentHandNum(0);
  };

  // Cleanup WebSocket on unmount
  useEffect(() => { return () => cleanupWs(); }, [cleanupWs]);

  // Get equity for a player
  const getEquity = (name: string, eqList: any[]) => {
    const eq = eqList.find((e: any) => e.player_id === name);
    return eq ? eq.win_pct : null;
  };

  // Review a completed hand
  const selectedHand = selectedHandIdx != null ? completedHands[selectedHandIdx] : null;

  // -- RENDER --
  return (
    <div>
      <h1 className="page-title">Hand Lab</h1>

      {/* === SETUP PHASE === */}
      {phase === 'setup' && (
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
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button className="btn btn-primary" onClick={() => handleStart(1)} disabled={!canRun || loading}>
              {loading ? 'Starting...' : 'Run Once'}
            </button>
            <button className="btn btn-primary" onClick={() => handleStart(runCount)} disabled={!canRun || loading}
              style={{ background: '#7c3aed' }}>
              Run {runCount} Times
            </button>
            <input type="number" value={runCount} onChange={e => setRunCount(+e.target.value)} min={2} max={100} style={{ width: 60 }} />
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>times</span>
          </div>
        </div>
      )}

      {/* === LIVE PHASE === */}
      {phase === 'live' && (
        <>
          <div className="card">
            <div className="flex-between mb-16">
              <h2>
                Live {totalHands > 1 ? `- Hand ${currentHandNum} / ${totalHands}` : ''}
              </h2>
              <button className="btn btn-danger" onClick={handleStop} style={{ padding: '8px 16px' }}>
                Stop
              </button>
            </div>

            {/* Poker Table */}
            <div className="poker-table" style={{ marginBottom: 16 }}>
              <div className="pot-display">Pot: {livePot}</div>
              <div className="community-cards">
                {liveCommunity.length > 0
                  ? liveCommunity.map((c, i) => <CardView key={i} card={c} />)
                  : [1, 2, 3, 4, 5].map(i => <CardView key={i} card="" />)
                }
              </div>
            </div>

            {/* Player Seats */}
            <div className="seats-container" style={{ marginBottom: 16 }}>
              {Object.entries(livePlayerCards).map(([pid, info]: [string, any]) => {
                const eq = getEquity(pid, liveEquity);
                const isThinking = thinkingPlayer === pid;
                const isFolded = liveActions.some((a: any) => a.player_id === pid && a.action === 'fold');
                return (
                  <div key={pid} className={`seat ${isThinking ? 'seat-thinking' : ''} ${isFolded ? 'seat-folded' : ''}`}>
                    <div className="name">
                      {pid}
                      {isThinking && <span className="thinking-dot"> ...</span>}
                    </div>
                    <div className="hole-cards">
                      {(info.hole_cards || []).map((c: string, i: number) => <CardView key={i} card={c} />)}
                    </div>
                    {eq != null && <EquityBar winPct={eq} label="Win" />}
                    <div className="chips">{info.chips} chips</div>
                  </div>
                );
              })}
            </div>

            {/* Live Action Stream */}
            {liveActions.length > 0 ? (
              <div className="timeline" ref={liveLogRef} style={{ maxHeight: 300, overflowY: 'auto' }}>
                {liveActions.map((a: any, i: number) => (
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
            ) : thinkingPlayer ? (
              <p style={{ color: '#94a3b8', padding: '12px' }}>{thinkingPlayer} is thinking...</p>
            ) : handInProgress ? (
              <p style={{ color: '#94a3b8', padding: '12px' }}>Cards dealt, waiting for actions...</p>
            ) : (
              <p className="empty-state">Waiting for hand to start...</p>
            )}
          </div>

          {/* Completed Hands So Far (during multi-run) */}
          {completedHands.length > 0 && totalHands > 1 && (
            <div className="card">
              <h2>Completed Hands ({completedHands.length})</h2>
              <div className="timeline">
                {completedHands.map((h, i) => (
                  <div key={i} className="timeline-item">
                    <span style={{ width: 30, color: '#64748b' }}>#{i + 1}</span>
                    <span style={{ flex: 1 }}>{h.community_cards?.join(' ') || 'no showdown'}</span>
                    <span className="text-yellow">Pot: {h.pot_total}</span>
                    {Object.entries(h.winners || {}).map(([name, amt]: [string, any]) => (
                      <span key={name} className="text-green" style={{ marginLeft: 8 }}>{name} +{amt}</span>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* === FINISHED PHASE === */}
      {phase === 'finished' && (
        <>
          <div style={{ marginBottom: 16 }}>
            <button className="btn btn-primary" onClick={handleBackToSetup}>
              Back to Setup
            </button>
          </div>

          {/* Multi-Run Summary */}
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
              <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                Average Pot: {multiSummary.avg_pot}
              </div>
            </div>
          )}

          {/* Hand List + Detail */}
          {completedHands.length > 0 && (
            <div className="card">
              <h2>Hands ({completedHands.length})</h2>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 16 }}>
                {completedHands.map((h, i) => (
                  <button key={i}
                    className={`btn btn-sm ${selectedHandIdx === i ? 'btn-primary' : ''}`}
                    onClick={() => setSelectedHandIdx(i)}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', minWidth: 44 }}>
                    #{i + 1}
                  </button>
                ))}
              </div>

              {selectedHand && (
                <>
                  {/* Poker Table for selected hand */}
                  <div className="poker-table" style={{ marginBottom: 16 }}>
                    <div className="pot-display">Pot: {selectedHand.pot_total}</div>
                    <div className="community-cards">
                      {(selectedHand.community_cards || []).map((c: string, i: number) => <CardView key={i} card={c} />)}
                    </div>
                  </div>

                  {/* Player results */}
                  <div className="seats-container" style={{ marginBottom: 16 }}>
                    {Object.entries(selectedHand.player_cards || {}).map(([pid, cards]: [string, any]) => {
                      const isWinner = selectedHand.winners && selectedHand.winners[pid];
                      const chipChange = selectedHand.chip_changes?.[pid];
                      const eq = selectedHand.equity ? getEquity(pid, selectedHand.equity) : null;
                      return (
                        <div key={pid} className="seat"
                          style={isWinner ? { border: '2px solid #22c55e' } : {}}>
                          <div className="name">{pid}</div>
                          <div className="hole-cards">
                            {cards.map((c: string, i: number) => <CardView key={i} card={c} />)}
                          </div>
                          {eq != null && <EquityBar winPct={eq} label="Win" />}
                          <div className="chips">{selectedHand.final_chips?.[pid]} chips</div>
                          {chipChange != null && chipChange !== 0 && (
                            <div className={chipChange > 0 ? 'chip-change-positive' : 'chip-change-negative'}>
                              {chipChange > 0 ? `+${chipChange}` : chipChange}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Action log for selected hand */}
                  {selectedHand.actions?.length > 0 && (
                    <div className="timeline" style={{ maxHeight: 300, overflowY: 'auto' }}>
                      {selectedHand.actions.map((a: any, i: number) => (
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
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
