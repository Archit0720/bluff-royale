const API = '/api';

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function q(path: string, options: RequestInit = {}) {
  const response = await fetch(API + path, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  let data: any;
  try {
    data = await response.json();
  } catch {
    const message = response.ok
      ? 'The server returned an unexpected response. Try again shortly.'
      : `The game server is temporarily unavailable (HTTP ${response.status}).`;
    throw new ApiError(message, response.status);
  }
  if (!response.ok) {
    throw new ApiError(data.detail || `Request failed (${response.status})`, response.status);
  }
  return data;
}

const post = (path: string, body?: unknown) =>
  q(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export const api = {
  nonce: () => q('/auth/nonce'),
  login: (credential: string, nonce: string) => post('/auth/google', { credential, nonce }),
  me: () => q('/auth/me'),
  logout: () => post('/auth/logout', {}),
  create: (player_name: string, deck_count = 1) =>
    post('/games', { player_name, deck_count }),
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
  emote: (
    gameId: string,
    emote: 'laugh' | 'wow' | 'clap' | 'heart' | 'bluff' | 'cool' | 'fire' | 'crown' | 'eyes' | 'sweat' | 'shrug',
  ) =>
    post(`/games/${gameId}/emote`, { emote }),
  dialogue: (
    gameId: string,
    message:
      | {
          dialogue:
            | 'arre_bhai'
            | 'kya_scene'
            | 'filmi_bluff'
            | 'chai_break'
            | 'seedha_bol'
            | 'wah_ustad'
            | 'dimaag_laga'
            | 'jugaad_pro'
            | 'balle_balle'
            | 'shabaash_sher'
            | 'rangey_haath'
            | 'kya_baat'
            | 'boss_move'
            | 'scene_set';
        }
      | { custom_text: string },
  ) => post(`/games/${gameId}/dialogue`, message),
  leave: (gameId: string) => post(`/games/${gameId}/leave`, {}),
  history: (_playerName?: string) => q('/auth/me/matches'),
};
