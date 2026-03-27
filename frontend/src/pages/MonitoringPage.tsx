import { useEffect, useState } from 'react';
import { api } from '../api/client';

export default function MonitoringPage() {
  const [overview, setOverview] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [agentMetrics, setAgentMetrics] = useState<any>(null);
  const [llmCalls, setLlmCalls] = useState<any[]>([]);

  useEffect(() => {
    api.getOverview().then(setOverview).catch(() => {});
    api.getProviders().then(setProviders).catch(() => {});
    api.listAgents().then(setAgents).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedAgent) { setAgentMetrics(null); setLlmCalls([]); return; }
    api.getAgentMetrics(selectedAgent).then(setAgentMetrics).catch(() => {});
    api.getAgentLLMCalls(selectedAgent).then(setLlmCalls).catch(() => {});
  }, [selectedAgent]);

  return (
    <div>
      <h1 className="page-title">Monitoring Center</h1>

      {/* Global overview */}
      {overview && (
        <div className="grid-4 mb-16">
          <div className="card stat">
            <div className="value">{overview.total_llm_calls}</div>
            <div className="label">LLM Calls</div>
          </div>
          <div className="card stat">
            <div className="value">{overview.total_tokens?.toLocaleString()}</div>
            <div className="label">Total Tokens</div>
          </div>
          <div className="card stat">
            <div className="value text-green">{overview.success_decisions}</div>
            <div className="label">Successful Decisions</div>
          </div>
          <div className="card stat">
            <div className="value text-red">{overview.timeout_decisions}</div>
            <div className="label">Timeouts</div>
          </div>
        </div>
      )}

      {/* Provider status */}
      <div className="card mb-16">
        <h2>LLM Provider Status</h2>
        {providers.length === 0 ? (
          <p className="empty-state">No LLM calls recorded yet</p>
        ) : (
          <table>
            <thead>
              <tr><th>Provider</th><th>Total Calls</th><th>Success</th><th>Errors</th><th>Availability</th><th>Avg Latency</th><th>P95 Latency</th></tr>
            </thead>
            <tbody>
              {providers.map(p => (
                <tr key={p.provider_name}>
                  <td><strong>{p.provider_name}</strong></td>
                  <td>{p.total_calls}</td>
                  <td className="text-green">{p.success_count}</td>
                  <td className={p.error_count > 0 ? 'text-red' : ''}>{p.error_count}</td>
                  <td className={p.availability_rate >= 0.95 ? 'text-green' : 'text-red'}>
                    {(p.availability_rate * 100).toFixed(1)}%
                  </td>
                  <td>{p.avg_latency_ms}ms</td>
                  <td>{p.p95_latency_ms}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Agent metrics drill-down */}
      <div className="card">
        <div className="flex-between mb-16">
          <h2>Agent Metrics</h2>
          <select style={{width:'auto', minWidth:180}} value={selectedAgent} onChange={e => setSelectedAgent(e.target.value)}>
            <option value="">Select an agent...</option>
            {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.display_name} ({a.agent_id})</option>)}
          </select>
        </div>

        {agentMetrics ? (
          <>
            <div className="grid-4 mb-16">
              <div className="stat">
                <div className="value">{agentMetrics.total_decisions}</div>
                <div className="label">Decisions</div>
              </div>
              <div className="stat">
                <div className="value text-green">{(agentMetrics.success_rate * 100).toFixed(1)}%</div>
                <div className="label">Success Rate</div>
              </div>
              <div className="stat">
                <div className="value text-red">{agentMetrics.timeout_count}</div>
                <div className="label">Timeouts</div>
              </div>
              <div className="stat">
                <div className="value">{agentMetrics.total_tokens.toLocaleString()}</div>
                <div className="label">Total Tokens</div>
              </div>
            </div>
            <div className="grid-3 mb-16">
              <div className="stat">
                <div className="value">{agentMetrics.avg_latency_ms}ms</div>
                <div className="label">Avg LLM Latency</div>
              </div>
              <div className="stat">
                <div className="value">{agentMetrics.p95_latency_ms}ms</div>
                <div className="label">P95 LLM Latency</div>
              </div>
              <div className="stat">
                <div className="value">{agentMetrics.retry_count}</div>
                <div className="label">Retries</div>
              </div>
            </div>

            {/* Recent LLM calls */}
            <h2 style={{marginTop:20}}>Recent LLM Calls</h2>
            <div style={{maxHeight:300, overflowY:'auto'}}>
              <table>
                <thead>
                  <tr><th>Provider</th><th>Model</th><th>In Tokens</th><th>Out Tokens</th><th>Latency</th><th>Status</th><th>Retry</th></tr>
                </thead>
                <tbody>
                  {llmCalls.slice(-30).reverse().map(c => (
                    <tr key={c.record_id}>
                      <td>{c.provider_name}</td>
                      <td style={{fontSize:'0.8rem'}}>{c.model_name}</td>
                      <td>{c.input_tokens}</td>
                      <td>{c.output_tokens}</td>
                      <td>{c.latency_ms}ms</td>
                      <td className={c.status === 'success' ? 'text-green' : 'text-red'}>{c.status}</td>
                      <td>{c.is_retry ? 'Yes' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="empty-state">Select an agent to view metrics</p>
        )}
      </div>
    </div>
  );
}
