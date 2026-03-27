import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';

function CardView({ card }: { card: string }) {
  const suit = card?.[1];
  const isRed = suit === 'h' || suit === 'd';
  const symbols: Record<string, string> = { h: '\u2665', d: '\u2666', c: '\u2663', s: '\u2660' };
  return <div className={`playing-card ${isRed ? 'red' : ''}`}>{card?.[0]}{symbols[suit] || ''}</div>;
}

export default function ReplayPage() {
  const { handId } = useParams<{ handId: string }>();
  const [hand, setHand] = useState<any>(null);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (handId) api.getHandDetail(handId).then(setHand).catch(e => alert(e.message));
  }, [handId]);

  if (!hand) return <div className="empty-state">Loading hand {handId}...</div>;

  const actions = hand.actions || [];
  const visibleActions = actions.slice(0, step + 1);
  const currentAction = actions[step];

  // Determine visible community cards based on current step's street
  const streetOrder = ['preflop', 'flop', 'turn', 'river'];
  const currentStreet = currentAction?.street || 'preflop';
  const streetIdx = streetOrder.indexOf(currentStreet);
  let visibleCards: string[] = [];
  if (streetIdx >= 1) visibleCards = hand.community_cards.slice(0, 3);
  if (streetIdx >= 2) visibleCards = hand.community_cards.slice(0, 4);
  if (streetIdx >= 3) visibleCards = hand.community_cards.slice(0, 5);

  return (
    <div>
      <h1 className="page-title">Replay: Hand {hand.hand_id}</h1>

      {/* Board */}
      <div className="poker-table" style={{minHeight: 280}}>
        <div className="pot-display">Pot: {currentAction?.pot_after || 0}</div>
        <div className="community-cards">
          {visibleCards.map((c: string, i: number) => <CardView key={i} card={c} />)}
          {Array.from({length: 5 - visibleCards.length}).map((_, i) => (
            <div key={`empty-${i}`} className="playing-card facedown">?</div>
          ))}
        </div>
      </div>

      {/* Replay controls */}
      <div className="card" style={{textAlign:'center'}}>
        <button className="btn btn-primary btn-sm" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
          Prev
        </button>
        <span style={{margin:'0 20px', fontSize:'0.9rem'}}>
          Step {step + 1} / {actions.length}
          {currentAction && ` - ${currentAction.street}: ${currentAction.player_id} ${currentAction.action}`}
        </span>
        <button className="btn btn-primary btn-sm" onClick={() => setStep(Math.min(actions.length - 1, step + 1))} disabled={step >= actions.length - 1}>
          Next
        </button>
        <button className="btn btn-sm" style={{marginLeft:12, background:'#334155', color:'#e2e8f0'}} onClick={() => setStep(actions.length - 1)}>
          End
        </button>
      </div>

      {/* Current action detail */}
      {currentAction && (
        <div className="grid-2">
          <div className="card">
            <h2>Action Detail</h2>
            <table>
              <tbody>
                <tr><td>Player</td><td><strong>{currentAction.player_id}</strong></td></tr>
                <tr><td>Street</td><td>{currentAction.street}</td></tr>
                <tr><td>Action</td><td><span className={`badge badge-${currentAction.action}`}>{currentAction.action}</span> {currentAction.amount > 0 && currentAction.amount}</td></tr>
                <tr><td>Pot After</td><td className="text-yellow">{currentAction.pot_after}</td></tr>
                {currentAction.is_timeout && <tr><td>Status</td><td className="text-red">TIMEOUT (auto-fold)</td></tr>}
                {currentAction.input_tokens > 0 && (
                  <tr><td>Tokens</td><td>{currentAction.input_tokens} in / {currentAction.output_tokens} out</td></tr>
                )}
                {currentAction.llm_latency_ms > 0 && (
                  <tr><td>LLM Latency</td><td>{currentAction.llm_latency_ms.toFixed(0)}ms</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="card">
            <h2>Agent Thinking</h2>
            {currentAction.thinking ? (
              <div className="thinking-panel" style={{maxHeight:200}}>{currentAction.thinking}</div>
            ) : (
              <p className="empty-state">No thinking data (human player or parse failure)</p>
            )}
          </div>
        </div>
      )}

      {/* Full timeline */}
      <div className="card mt-12">
        <h2>Full Timeline</h2>
        <div className="timeline">
          {actions.map((a: any, i: number) => (
            <div key={i} className="timeline-item"
              style={{cursor:'pointer', background: i === step ? '#334155' : undefined}}
              onClick={() => setStep(i)}>
              <span style={{width:30, color:'#64748b'}}>#{i+1}</span>
              <span style={{width:70, color:'#94a3b8', fontWeight:600}}>{a.street}</span>
              <span style={{width:90}}>{a.player_id}</span>
              <span className={`badge badge-${a.action}`}>{a.action}</span>
              {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
              {a.is_timeout && <span className="text-red" style={{marginLeft:4}}>[TIMEOUT]</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
