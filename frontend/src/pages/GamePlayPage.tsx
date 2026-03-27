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
  const wsRef = useRef<WebSocket | null>(null);

  // Poll game status
  useEffect(() => {
    if (!sessionId) return;
    const poll = () => {
      api.getGame(sessionId).then(setGame).catch(() => {});
      api.getGameHands(sessionId).then(h => { setHands(h); if (h.length > 0 && !selectedHand) setSelectedHand(h[h.length - 1]); }).catch(() => {});
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
      }
    };
    return () => ws.close();
  }, [sessionId]);

  const lastHand = selectedHand || (hands.length > 0 ? hands[hands.length - 1] : null);

  return (
    <div>
      <div className="flex-between mb-16">
        <h1 className="page-title">Game: {sessionId}</h1>
        <span className={`tag ${game?.status === 'finished' ? 'tag-expert' : 'tag-intermediate'}`}>
          {game?.status || 'loading'}
        </span>
      </div>

      {/* Poker Table */}
      <div className="poker-table">
        {lastHand ? (
          <>
            <div className="pot-display">Pot: {lastHand.pot_total}</div>
            <div className="community-cards">
              {lastHand.community_cards?.length > 0
                ? lastHand.community_cards.map((c: string, i: number) => <CardView key={i} card={c} />)
                : [1,2,3,4,5].map(i => <CardView key={i} card="" />)
              }
            </div>
          </>
        ) : (
          <div className="pot-display">Waiting for game...</div>
        )}
      </div>

      {/* Seats */}
      {game?.current_chips && (
        <div className="seats-container">
          {Object.entries(game.current_chips).map(([pid, chips]) => (
            <div key={pid} className="seat">
              <div className="name">{pid}</div>
              <div className="chips">{String(chips)} chips</div>
              {lastHand?.winners?.[pid] && <div className="text-green" style={{fontSize:'0.85rem'}}>+{lastHand.winners[pid]}</div>}
            </div>
          ))}
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
          {selectedHand?.actions ? (
            <div className="timeline">
              {selectedHand.actions.map((a: any, i: number) => (
                <div key={i}>
                  <div className="timeline-item">
                    <span style={{width:70, color:'#64748b', fontWeight:600}}>{a.street}</span>
                    <span style={{width:90}}>{a.player_id}</span>
                    <ActionBadge action={a.action} />
                    {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
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
