import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

export default function DashboardPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [games, setGames] = useState<any[]>([]);
  const [overview, setOverview] = useState<any>(null);

  useEffect(() => {
    api.listAgents().then(setAgents).catch(() => {});
    api.listGames().then(setGames).catch(() => {});
    api.getOverview().then(setOverview).catch(() => {});
  }, []);

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>

      {overview && (
        <div className="grid-4 mb-16">
          <div className="card stat">
            <div className="value">{agents.length}</div>
            <div className="label">Agents</div>
          </div>
          <div className="card stat">
            <div className="value">{games.length}</div>
            <div className="label">Games</div>
          </div>
          <div className="card stat">
            <div className="value">{overview.total_decisions}</div>
            <div className="label">Total Decisions</div>
          </div>
          <div className="card stat">
            <div className="value">{overview.total_tokens?.toLocaleString()}</div>
            <div className="label">Total Tokens</div>
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <div className="flex-between mb-16">
            <h2>Agents</h2>
            <Link to="/agents" className="btn btn-primary btn-sm">Manage</Link>
          </div>
          {agents.length === 0 ? (
            <p className="empty-state">No agents yet. Create one to get started.</p>
          ) : (
            <table>
              <thead><tr><th>Name</th><th>Style</th><th>Hands</th></tr></thead>
              <tbody>
                {agents.slice(0, 5).map(a => (
                  <tr key={a.agent_id}>
                    <td>{a.display_name}</td>
                    <td><span className={`tag tag-${a.skill_level}`}>{a.play_style.toUpperCase()}</span></td>
                    <td>{a.total_hands}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <div className="flex-between mb-16">
            <h2>Recent Games</h2>
            <Link to="/games/new" className="btn btn-primary btn-sm">New Game</Link>
          </div>
          {games.length === 0 ? (
            <p className="empty-state">No games yet.</p>
          ) : (
            <table>
              <thead><tr><th>Session</th><th>Status</th><th>Blinds</th></tr></thead>
              <tbody>
                {games.slice(0, 5).map(g => (
                  <tr key={g.session_id}>
                    <td><Link to={`/games/${g.session_id}`} style={{color:'#22d3ee'}}>{g.session_id}</Link></td>
                    <td><span className={`tag ${g.status === 'finished' ? 'tag-expert' : 'tag-intermediate'}`}>{g.status}</span></td>
                    <td>{g.small_blind}/{g.big_blind}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
