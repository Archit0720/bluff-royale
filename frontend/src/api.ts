const API = import.meta.env.VITE_API_URL || window.location.origin;

async function q(path: string, options: RequestInit = {}) {
  const response = await fetch(API + path, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({ detail: 'Invalid server response' }));
  if (!response.ok) throw Error(data.detail || `Request failed (${response.status})`);
  return data;
}

const post = (path: string, body?: unknown) =>
  q(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const api = {
  nonce: () => q('/auth/nonce'),
  login: (credential: string, nonce: string) => {
    if (import.meta.env.PROD && new URL(API, window.location.href).protocol !== 'https:') {
      throw Error('Google sign-in requires an HTTPS API endpoint in production.');
    }
    return post('/auth/google', { credential, nonce });
  },
  me: () => q('/auth/me'),
  logout: () => post('/auth/logout', {}),
  create: (player_name: string) => post('/games', { player_name }),
  join: (gameId: string, player_name: string) =>
    post(`/games/${gameId}/join`, { player_name }),
  room: (gameId: string) => q(`/games/${gameId}`),
  start: (gameId: string) => post(`/games/${gameId}/start`),
  state: (gameId: string, _playerId?: string) => q(`/games/${gameId}/state`),
  play: (gameId: string, _playerId: string, card_indices: number[], claimed_rank?: string) =>
    post(`/games/${gameId}/play`, { card_indices, claimed_rank }),
  skip: (gameId: string, _playerId?: string) => post(`/games/${gameId}/skip`, {}),
  closeRound: (gameId: string, _playerId?: string) => post(`/games/${gameId}/close-round`, {}),
  challenge: (gameId: string, _playerId?: string) => post(`/games/${gameId}/challenge`, {}),
  pause: (gameId: string, _playerId?: string) => post(`/games/${gameId}/pause`, {}),
  resume: (gameId: string, _playerId?: string) => post(`/games/${gameId}/resume`, {}),
  history: (_playerName?: string) => q('/auth/me/matches'),
};
