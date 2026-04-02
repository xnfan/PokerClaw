import { useState } from 'react';

const RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
const SUITS = [
  { key: 's', symbol: '\u2660', color: '#e2e8f0' },
  { key: 'h', symbol: '\u2665', color: '#f87171' },
  { key: 'd', symbol: '\u2666', color: '#60a5fa' },
  { key: 'c', symbol: '\u2663', color: '#4ade80' },
];

interface CardPickerProps {
  selectedCards: string[];
  maxCards: number;
  usedCards: string[];
  onChange: (cards: string[]) => void;
}

export default function CardPicker({ selectedCards, maxCards, usedCards, onChange }: CardPickerProps) {
  const [open, setOpen] = useState(false);

  const toggle = (card: string) => {
    if (selectedCards.includes(card)) {
      onChange(selectedCards.filter(c => c !== card));
    } else if (selectedCards.length < maxCards) {
      onChange([...selectedCards, card]);
    }
  };

  const isUsed = (card: string) => usedCards.includes(card) && !selectedCards.includes(card);

  return (
    <div>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
        {selectedCards.map(c => (
          <span key={c} className={`playing-card ${c[1] === 'h' || c[1] === 'd' ? 'red' : ''}`}
            style={{ cursor: 'pointer', fontSize: '0.8rem' }}
            onClick={() => toggle(c)}>
            {c[0]}{SUITS.find(s => s.key === c[1])?.symbol}
          </span>
        ))}
        {selectedCards.length < maxCards && (
          <button className="btn btn-sm" onClick={() => setOpen(!open)}
            style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
            {open ? 'Close' : `Pick (${selectedCards.length}/${maxCards})`}
          </button>
        )}
        {selectedCards.length > 0 && (
          <button className="btn btn-sm" onClick={() => onChange([])}
            style={{ padding: '4px 8px', fontSize: '0.7rem', color: '#f87171' }}>
            Clear
          </button>
        )}
      </div>
      {open && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(13, 1fr)`,
          gap: 2,
          marginTop: 8,
          background: '#0f172a',
          padding: 8,
          borderRadius: 8,
          maxWidth: 560,
        }}>
          {SUITS.map(suit => (
            RANKS.map(rank => {
              const card = `${rank}${suit.key}`;
              const selected = selectedCards.includes(card);
              const used = isUsed(card);
              return (
                <button
                  key={card}
                  onClick={() => !used && toggle(card)}
                  disabled={used}
                  style={{
                    padding: '4px 2px',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    border: selected ? '2px solid #0ea5e9' : '1px solid #334155',
                    borderRadius: 4,
                    background: selected ? '#0ea5e933' : used ? '#1e293b44' : '#1e293b',
                    color: used ? '#475569' : suit.color,
                    cursor: used ? 'not-allowed' : 'pointer',
                    minWidth: 32,
                  }}>
                  {rank}{suit.symbol}
                </button>
              );
            })
          ))}
        </div>
      )}
    </div>
  );
}
