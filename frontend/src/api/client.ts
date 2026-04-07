const BASE = 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  // Agents
  listAgents: () => request<any[]>('/api/agents'),
  createAgent: (data: any) => request<any>('/api/agents', { method: 'POST', body: JSON.stringify(data) }),
  deleteAgent: (id: string) => request<any>(`/api/agents/${id}`, { method: 'DELETE' }),
  getAgent: (id: string) => request<any>(`/api/agents/${id}`),

  // Games
  createGame: (data: any) => request<any>('/api/games', { method: 'POST', body: JSON.stringify(data) }),
  startGame: (sessionId: string, numHands: number) =>
    request<any>(`/api/games/${sessionId}/start?num_hands=${numHands}`, { method: 'POST' }),
  listGames: () => request<any[]>('/api/games'),
  getGame: (sessionId: string) => request<any>(`/api/games/${sessionId}`),
  getGameHands: (sessionId: string) => request<any[]>(`/api/games/${sessionId}/hands`),
  stopGame: (sessionId: string) => request<any>(`/api/games/${sessionId}/stop`, { method: 'POST' }),

  // Replay
  getHandDetail: (handId: string) => request<any>(`/api/replay/hands/${handId}`),

  // Monitoring
  getAgentMetrics: (agentId: string) => request<any>(`/api/monitoring/agents/${agentId}`),
  getAgentLLMCalls: (agentId: string) => request<any[]>(`/api/monitoring/agents/${agentId}/llm-calls`),
  getOverview: () => request<any>('/api/monitoring/overview'),
  getProviders: () => request<any[]>('/api/monitoring/providers'),

  // Equity
  calculateEquity: (data: { players: string[][], community?: string[], num_simulations?: number }) =>
    request<any>('/api/equity', { method: 'POST', body: JSON.stringify(data) }),

  // Hand Lab
  runLabOnce: (data: any) => request<any>('/api/handlab/run-once', { method: 'POST', body: JSON.stringify(data) }),
  runLabMultiple: (data: any) => request<any>('/api/handlab/run-multiple', { method: 'POST', body: JSON.stringify(data) }),
  startLab: (data: { scenario: any; count?: number }) =>
    request<{ session_id: string }>('/api/handlab/start', { method: 'POST', body: JSON.stringify(data) }),

  // Human vs AI
  createHumanGame: (data: { agent_ids: string[]; human_name: string; small_blind?: number; big_blind?: number; buy_in?: number; num_hands?: number }) =>
    request<{ session_id: string; human_player_id: string }>('/api/games/human', { method: 'POST', body: JSON.stringify(data) }),
};

export function createGameWS(sessionId: string): WebSocket {
  return new WebSocket(`ws://localhost:8000/ws/game/${sessionId}`);
}
