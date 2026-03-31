import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, createGameWS } from '../api/client';

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

export default function GamePlayPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [game, setGame] = useState<any>(null);
  const [hands, setHands] = useState<any[]>([]);
  const [selectedHand, setSelectedHand] = useState<any>(null);
  // Real-time state
  const [liveActions, setLiveActions] = useState<any[]>([]);
  const [liveCommunity, setLiveCommunity] = useState<string[]>([]);
  const [livePot, setLivePot] = useState(0);
  const [thinkingPlayer, setThinkingPlayer] = useState<string | null>(null);
  const [currentHandId, setCurrentHandId] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const liveLogRef = useRef<HTMLDivElement>(null);

  // Poll game status
  useEffect(() => {
    if (!sessionId) return;
    const poll = () => {
      api.getGame(sessionId).then(setGame).catch(() => {});
      api.getGameHands(sessionId).then(h => {
        setHands(h);
        if (h.length > 0 && !selectedHand) setSelectedHand(h[h.length - 1]);
      }).catch(() => {});
    };
    poll();
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, [sessionId]);

  // WebSocket for real-time updates
  useEffect(() => {
    if (!sessionId) return;
    const ws = createGameWS(sessionId);
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'hand_complete') {
        setHands(prev => [...prev, msg.data]);
        setSelectedHand(msg.data);
        // Clear live state for next hand
        setLiveActions([]);
        setLiveCommunity([]);
        setLivePot(0);
        setThinkingPlayer(null);
        setCurrentHandId(null);
      } else if (msg.type === 'street_start') {
        setCurrentHandId(msg.data.hand_id);
        setLiveCommunity(msg.data.community_cards || []);
        setLivePot(msg.data.pot || 0);
        setThinkingPlayer(null);
      } else if (msg.type === 'player_thinking') {
        setCurrentHandId(msg.data.hand_id);
        setThinkingPlayer(msg.data.player_id);
      } else if (msg.type === 'player_action') {
        setThinkingPlayer(null);
        setLivePot(msg.data.pot_after || 0);
        setLiveActions(prev => [...prev, msg.data]);
      }
    };
    return () => ws.close();
  }, [sessionId]);

  // Auto-scroll live action log
  useEffect(() => {
    if (liveLogRef.current) {
      liveLogRef.current.scrollTop = liveLogRef.current.scrollHeight;
    }
  }, [liveActions]);

  const handleStop = async () => {
    if (!sessionId) return;
    setStopping(true);
    try {
      await api.stopGame(sessionId);
    } catch (e: any) {
      alert(e.message);
      setStopping(false);
    }
  };

  const lastHand = selectedHand || (hands.length > 0 ? hands[hands.length - 1] : null);
  const isRunning = game?.status === 'running';
  const isLive = isRunning && (liveActions.length > 0 || thinkingPlayer);

  // Use live community cards during active play, otherwise last hand's
  const displayCommunity = isLive ? liveCommunity : (lastHand?.community_cards || []);
  const displayPot = isLive ? livePot : (lastHand?.pot_total || 0);

  return (
    <div>
      <div className="flex-between mb-16">
        <h1 className="page-title">Game: {sessionId}</h1>
        <div style={{display: 'flex', gap: 8, alignItems: 'center'}}>
          {isRunning && (
            <button
              className="btn btn-danger"
              onClick={handleStop}
              disabled={stopping}
              style={{padding: '8px 20px'}}
            >
              {stopping ? 'Stopping...' : 'Stop Game'}
            </button>
          )}
          <span className={`tag ${game?.status === 'finished' ? 'tag-expert' : 'tag-intermediate'}`}>
            {game?.status || 'loading'}
          </span>
        </div>
      </div>

      {/* Poker Table */}
      <div className="poker-table">
        {lastHand || isLive ? (
          <>
            <div className="pot-display">Pot: {displayPot}</div>
            <div className="community-cards">
              {displayCommunity.length > 0
                ? displayCommunity.map((c: string, i: number) => <CardView key={i} card={c} />)
                : [1,2,3,4,5].map(i => <CardView key={i} card="" />)
              }
            </div>
          </>
        ) : (
          <div className="pot-display">Waiting for game...</div>
        )}
      </div>

      {/* Seats with chip changes */}
      {game?.current_chips && (
        <div className="seats-container">
          {Object.entries(game.current_chips).map(([pid, chips]) => {
            const isThinking = thinkingPlayer === pid;
            const chipChange = lastHand?.chip_changes?.[pid];
            return (
              <div key={pid} className={`seat ${isThinking ? 'seat-thinking' : ''}`}>
                <div className="name">
                  {pid}
                  {isThinking && <span className="thinking-dot"> ...</span>}
                </div>
                <div className="chips">{String(chips)} chips</div>
                {chipChange != null && chipChange !== 0 && !isLive && (
                  <div className={chipChange > 0 ? 'chip-change-positive' : 'chip-change-negative'}>
                    {chipChange > 0 ? `+${chipChange}` : chipChange}
                  </div>
                )}
                {lastHand?.winners?.[pid] && !chipChange && (
                  <div className="text-green" style={{fontSize:'0.85rem'}}>+{lastHand.winners[pid]}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Live Action Stream (during game) */}
      {isRunning && (
        <div className="card">
          <h2>Live Actions {currentHandId ? `- Hand ${currentHandId}` : ''}</h2>
          {liveActions.length > 0 ? (
            <div className="timeline" ref={liveLogRef} style={{maxHeight: 300}}>
              {liveActions.map((a: any, i: number) => (
                <div key={i}>
                  <div className="timeline-item">
                    <span style={{width:70, color:'#64748b', fontWeight:600}}>{a.street}</span>
                    <span style={{width:90}}>{a.player_id}</span>
                    <ActionBadge action={a.action} />
                    {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
                    {a.round_bet > 0 && (
                      <span style={{marginLeft:8, fontSize:'0.75rem', color:'#94a3b8'}}>
                        Round: {a.round_bet}
                      </span>
                    )}
                    <span style={{marginLeft:'auto', fontSize:'0.75rem', color:'#64748b'}}>
                      Pot: {a.pot_after}
                    </span>
                  </div>
                  {a.thinking && <div className="thinking-panel">{a.thinking}</div>}
                </div>
              ))}
            </div>
          ) : thinkingPlayer ? (
            <p style={{color:'#94a3b8', padding: '12px'}}>{thinkingPlayer} is thinking...</p>
          ) : (
            <p className="empty-state">Waiting for actions...</p>
          )}
        </div>
      )}

      <div className="grid-2 mt-12">
        {/* Hand list */}
        <div className="card">
          <h2>Hands ({hands.length})</h2>
          <div className="timeline">
            {hands.map((h, i) => (
              <div key={h.hand_id} className="timeline-item" style={{cursor:'pointer'}}
                onClick={() => setSelectedHand(h)}>
                <span style={{width:30, color:'#64748b'}}>#{h.hand_number}</span>
                <span style={{flex:1}}>{h.community_cards?.join(' ') || 'no showdown'}</span>
                <span className="text-yellow">Pot: {h.pot_total}</span>
                <Link to={`/replay/${h.hand_id}`} className="btn btn-sm btn-primary" style={{marginLeft:8}}>Replay</Link>
              </div>
            ))}
          </div>
        </div>

        {/* Action log for selected hand */}
        <div className="card">
          <h2>Actions {selectedHand ? `- Hand #${selectedHand.hand_number}` : ''}</h2>

          {/* Chip changes summary */}
          {selectedHand?.chip_changes && (
            <div style={{display:'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap'}}>
              {Object.entries(selectedHand.chip_changes).map(([pid, change]: [string, any]) => (
                <span key={pid} style={{fontSize:'0.8rem'}}>
                  {pid}: <span className={change > 0 ? 'text-green' : change < 0 ? 'text-red' : 'text-yellow'}>
                    {change > 0 ? `+${change}` : change}
                  </span>
                </span>
              ))}
            </div>
          )}

          {selectedHand?.actions ? (
            <div className="timeline">
              {selectedHand.actions.map((a: any, i: number) => (
                <div key={i}>
                  <div className="timeline-item">
                    <span style={{width:70, color:'#64748b', fontWeight:600}}>{a.street}</span>
                    <span style={{width:90}}>{a.player_id}</span>
                    <ActionBadge action={a.action} />
                    {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
                    {a.round_bet > 0 && (
                      <span style={{marginLeft:8, fontSize:'0.75rem', color:'#94a3b8'}}>
                        Round: {a.round_bet}
                      </span>
                    )}
                    {a.is_timeout && <span className="badge badge-fold" style={{marginLeft:4}}>TIMEOUT</span>}
                    {a.input_tokens > 0 && (
                      <span style={{marginLeft:'auto', fontSize:'0.75rem', color:'#64748b'}}>
                        {a.input_tokens}+{a.output_tokens}tok / {a.llm_latency_ms?.toFixed(0)}ms
                      </span>
                    )}
                  </div>
                  {a.thinking && <div className="thinking-panel">{a.thinking}</div>}
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state">Select a hand to view actions</p>
          )}
        </div>
      </div>
    </div>
  );
}
