import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
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
  const [searchParams] = useSearchParams();
  const isHumanPlayer = searchParams.get('human') === 'true';
  const [game, setGame] = useState<any>(null);
  const [hands, setHands] = useState<any[]>([]);
  const [selectedHand, setSelectedHand] = useState<any>(null);
  // Real-time state
  const [liveActions, setLiveActions] = useState<any[]>([]);
  const [liveCommunity, setLiveCommunity] = useState<string[]>([]);
  const [livePot, setLivePot] = useState(0);
  const [thinkingPlayer, setThinkingPlayer] = useState<string | null>(null);
  const [currentHandId, setCurrentHandId] = useState<string | null>(null);
  const [livePlayerCards, setLivePlayerCards] = useState<Record<string, string[]>>({});
  const [handInProgress, setHandInProgress] = useState(false);
  const [stopping, setStopping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const liveLogRef = useRef<HTMLDivElement>(null);
  // Track game status from WebSocket events (more reliable than polling)
  const [wsGameActive, setWsGameActive] = useState(false);
  // Human player state
  const [isMyTurn, setIsMyTurn] = useState(false);
  const [validActions, setValidActions] = useState<string[]>([]);
  const [callAmount, setCallAmount] = useState(0);
  const [minRaise, setMinRaise] = useState(0);
  const [maxRaise, setMaxRaise] = useState(0);
  const [raiseAmount, setRaiseAmount] = useState(0);
  const [turnTimeLeft, setTurnTimeLeft] = useState(0);
  // Dealer and blinds positions
  const [dealerPos, setDealerPos] = useState<string | null>(null);
  const [smallBlindPos, setSmallBlindPos] = useState<string | null>(null);
  const [bigBlindPos, setBigBlindPos] = useState<string | null>(null);
  const [blindsAmount, setBlindsAmount] = useState({ sb: 50, bb: 100 });

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
    const iv = setInterval(poll, 3000);
    return () => clearInterval(iv);
  }, [sessionId]);

  // WebSocket for real-time updates
  useEffect(() => {
    if (!sessionId) return;
    const ws = createGameWS(sessionId);
    wsRef.current = ws;
    ws.onopen = () => {
      console.log('[WS] connected for session', sessionId);
      setWsGameActive(true);
    };
    ws.onclose = () => {
      console.log('[WS] disconnected');
    };
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      console.log('[WS] event:', msg.type, msg.data);
      if (msg.type === 'hand_complete') {
        setHands(prev => [...prev, msg.data]);
        setSelectedHand(msg.data);
        // Mark hand as done, but keep live state visible until next hand starts
        setHandInProgress(false);
        setThinkingPlayer(null);
        // Refresh game data to get updated chips
        api.getGame(sessionId).then(setGame).catch(() => {});
      } else if (msg.type === 'hand_start') {
        setCurrentHandId(msg.data.hand_id);
        setHandInProgress(true);
        // Store all player cards - filtering will happen at render time
        const playerCards: Record<string, string[]> = {};
        const playersData = msg.data.players || {};
        for (const [name, info] of Object.entries(playersData) as [string, any][]) {
          playerCards[name] = info.hole_cards || [];
        }
        setLivePlayerCards(playerCards);
        setLivePot(msg.data.pot || 0);
        setLiveActions([]);
        setLiveCommunity([]);
        setThinkingPlayer(null);
        // Store dealer and blinds positions
        setDealerPos(msg.data.dealer || null);
        setSmallBlindPos(msg.data.small_blind || null);
        setBigBlindPos(msg.data.big_blind || null);
        setBlindsAmount({
          sb: msg.data.small_blind_amount || 50,
          bb: msg.data.big_blind_amount || 100,
        });
      } else if (msg.type === 'street_start') {
        setLiveCommunity(msg.data.community_cards || []);
        setLivePot(msg.data.pot || 0);
        setThinkingPlayer(null);
      } else if (msg.type === 'player_thinking') {
        setCurrentHandId(msg.data.hand_id);
        setThinkingPlayer(msg.data.player_id);
      } else if (msg.type === 'human_turn') {
        // Human player's turn to act
        if (isHumanPlayer) {
          setIsMyTurn(true);
          setValidActions(msg.data.valid_actions || []);
          setCallAmount(msg.data.call_amount || 0);
          setMinRaise(msg.data.min_raise || 0);
          setMaxRaise(msg.data.max_raise || 0);
          setRaiseAmount(msg.data.min_raise || 0);
          setTurnTimeLeft(msg.data.timeout_seconds || 60);
        }
      } else if (msg.type === 'player_action') {
        setThinkingPlayer(null);
        setLivePot(msg.data.pot_after || 0);
        setLiveActions(prev => [...prev, msg.data]);
        // If this was my action, clear my turn state
        if (isHumanPlayer && msg.data.player_id === game?.human_player_id) {
          setIsMyTurn(false);
        }
      } else if (msg.type === 'game_finished') {
        setWsGameActive(false);
        setHandInProgress(false);
        setThinkingPlayer(null);
        api.getGame(sessionId).then(setGame).catch(() => {});
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

  // Countdown timer for human turn
  useEffect(() => {
    if (!isMyTurn || turnTimeLeft <= 0) return;
    const timer = setInterval(() => {
      setTurnTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [isMyTurn, turnTimeLeft]);

  const handleHumanAction = (action: string, amount: number = 0) => {
    if (!wsRef.current || !isMyTurn) return;
    wsRef.current.send(JSON.stringify({
      type: 'human_decision',
      player_id: game?.human_player_id,
      action,
      amount,
    }));
    setIsMyTurn(false);
  };

  const handleStop = async () => {
    if (!sessionId) return;
    setStopping(true);
    try {
      await api.stopGame(sessionId);
    } catch (e: any) {
      alert(e.message);
    }
    // Don't reset stopping — will be updated when game finishes via polling
  };

  const lastHand = selectedHand || (hands.length > 0 ? hands[hands.length - 1] : null);
  const isRunning = game?.status === 'running' || game?.status === 'pending_start';
  // Live when we have received hand_start but not yet hand_complete
  const isLive = handInProgress;

  // Use live community cards during active play, otherwise last hand's
  const displayCommunity = isLive ? liveCommunity : (lastHand?.community_cards || []);
  const displayPot = isLive ? livePot : (lastHand?.pot_total || 0);

  // Determine player cards to show: live cards during play, or last hand's cards when reviewing
  const displayPlayerCards = isLive ? livePlayerCards : (lastHand?.player_cards || {});

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
            <div className="pot-display">
              Pot: {displayPot}
              {isLive && (
                <span style={{ marginLeft: 16, fontSize: '0.85rem', color: '#94a3b8' }}>
                  SB: {blindsAmount.sb} / BB: {blindsAmount.bb}
                </span>
              )}
            </div>
            <div className="community-cards">
              {displayCommunity.length > 0
                ? displayCommunity.map((c: string, i: number) => <CardView key={i} card={c} />)
                : [1,2,3,4,5].map(i => <CardView key={i} card="" />)
              }
            </div>
            {/* Position legend */}
            {isLive && (
              <div style={{ marginTop: 12, fontSize: '0.75rem', color: '#64748b' }}>
                <span style={{ color: '#22c55e', fontWeight: 'bold' }}>[D]</span> Dealer{' '}
                <span style={{ color: '#eab308', fontWeight: 'bold', marginLeft: 8 }}>[SB]</span> Small Blind{' '}
                <span style={{ color: '#ef4444', fontWeight: 'bold', marginLeft: 8 }}>[BB]</span> Big Blind
              </div>
            )}
          </>
        ) : (
          <div className="pot-display">Waiting for game...</div>
        )}
      </div>

      {/* Seats with hole cards and chip changes */}
      {game?.current_chips && (
        <div className="seats-container">
          {Object.entries(game.current_chips).map(([pid, chips]) => {
            const isThinking = thinkingPlayer === pid;
            const chipChange = lastHand?.chip_changes?.[pid];
            const playerCards: string[] = displayPlayerCards[pid] || [];
            const isFolded = liveActions.some((a: any) => a.player_id === pid && a.action === 'fold');
            // Determine if this is the human player (for human vs AI mode)
            const isHumanSeat = isHumanPlayer && pid.toLowerCase().replace(' ', '_').includes(game.human_player_id?.replace('human_', '') || '');
            // Show cards if: spectator mode, or it's the human player's own seat, or game is finished
            const shouldShowCards = !isHumanPlayer || isHumanSeat || !isLive;
            // Determine position markers
            const isDealer = pid === dealerPos;
            const isSmallBlind = pid === smallBlindPos;
            const isBigBlind = pid === bigBlindPos;
            return (
              <div key={pid} className={`seat ${isThinking ? 'seat-thinking' : ''} ${isFolded && isLive ? 'seat-folded' : ''}`}>
                <div className="name">
                  {pid}
                  {isThinking && <span className="thinking-dot"> ...</span>}
                  {/* Position markers */}
                  {isDealer && <span style={{ marginLeft: 4, color: '#22c55e', fontWeight: 'bold' }}>[D]</span>}
                  {isSmallBlind && <span style={{ marginLeft: 4, color: '#eab308', fontWeight: 'bold' }}>[SB]</span>}
                  {isBigBlind && <span style={{ marginLeft: 4, color: '#ef4444', fontWeight: 'bold' }}>[BB]</span>}
                </div>
                {/* Show hole cards — only show human player's own cards in human mode */}
                {playerCards.length > 0 && shouldShowCards && (
                  <div className="hole-cards">
                    {playerCards.map((c: string, i: number) => <CardView key={i} card={c} />)}
                  </div>
                )}
                {/* Show facedown cards for other players in human mode */}
                {playerCards.length > 0 && !shouldShowCards && (
                  <div className="hole-cards">
                    <CardView key={0} card="" />
                    <CardView key={1} card="" />
                  </div>
                )}
                <div className="chips">{String(chips)} chips</div>
                {chipChange != null && chipChange !== 0 && !isLive && (
                  <div className={chipChange > 0 ? 'chip-change-positive' : 'chip-change-negative'}>
                    {chipChange > 0 ? `+${chipChange}` : chipChange}
                  </div>
                )}
                {lastHand?.winners?.[pid] && !chipChange && !isLive && (
                  <div className="text-green" style={{fontSize:'0.85rem'}}>+{lastHand.winners[pid]}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Human Player Controls */}
      {isHumanPlayer && isRunning && (
        <div className="card" style={{ background: isMyTurn ? '#0f172a' : '#1e293b' }}>
          <h2>
            {isMyTurn ? (
              <>
                Your Turn
                <span style={{ marginLeft: 12, color: turnTimeLeft <= 10 ? '#ef4444' : '#22c55e', fontSize: '1.2rem' }}>
                  {turnTimeLeft}s
                </span>
              </>
            ) : (
              'Waiting for your turn...'
            )}
          </h2>
          {isMyTurn && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {validActions.includes('fold') && (
                  <button
                    className="btn btn-danger"
                    onClick={() => handleHumanAction('fold')}
                    style={{ padding: '12px 24px', fontSize: '1rem' }}
                  >
                    Fold
                  </button>
                )}
                {validActions.includes('check') && (
                  <button
                    className="btn btn-primary"
                    onClick={() => handleHumanAction('check')}
                    style={{ padding: '12px 24px', fontSize: '1rem' }}
                  >
                    Check
                  </button>
                )}
                {validActions.includes('call') && (
                  <button
                    className="btn btn-primary"
                    onClick={() => handleHumanAction('call', callAmount)}
                    style={{ padding: '12px 24px', fontSize: '1rem' }}
                  >
                    Call {callAmount > 0 && `(${callAmount})`}
                  </button>
                )}
                {validActions.includes('raise') && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      className="btn btn-success"
                      onClick={() => handleHumanAction('raise', raiseAmount)}
                      style={{ padding: '12px 24px', fontSize: '1rem' }}
                    >
                      Raise
                    </button>
                    <input
                      type="number"
                      value={raiseAmount}
                      onChange={(e) => setRaiseAmount(Math.max(minRaise, Math.min(maxRaise, parseInt(e.target.value) || 0)))}
                      min={minRaise}
                      max={maxRaise}
                      style={{ width: 100, padding: '8px' }}
                    />
                    <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                      Min: {minRaise} / Max: {maxRaise}
                    </span>
                  </div>
                )}
                {validActions.includes('all_in') && (
                  <button
                    className="btn btn-warning"
                    onClick={() => handleHumanAction('all_in', maxRaise)}
                    style={{ padding: '12px 24px', fontSize: '1rem' }}
                  >
                    All-in ({maxRaise})
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Live Action Stream (during game) */}
      {isRunning && (
        <div className="card">
          <h2>Live Actions {currentHandId ? `- Hand ${currentHandId}` : ''}</h2>
          {liveActions.length > 0 ? (
            <div className="timeline" ref={liveLogRef} style={{maxHeight: 300, overflowY: 'auto'}}>
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
          ) : Object.keys(livePlayerCards).length > 0 ? (
            <p style={{color:'#94a3b8', padding: '12px'}}>Cards dealt, waiting for actions...</p>
          ) : (
            <p className="empty-state">Waiting for hand to start...</p>
          )}
        </div>
      )}

      <div className="grid-2 mt-12">
        {/* Hand list */}
        <div className="card">
          <h2>Hands ({hands.length})</h2>
          <div className="timeline">
            {hands.map((h) => (
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
