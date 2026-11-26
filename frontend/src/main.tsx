import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ApiError, api } from './api';
import GoogleSignIn from './GoogleSignIn';
import RoyaleTable from './RoyaleTable';
import { useRoyaleAudio } from './royale-audio';
import './style.css';
import './entry-flow.css';

type Screen =
  | 'splash'
  | 'menu'
  | 'signin'
  | 'play'
  | 'rules'
  | 'options'
  | 'history'
  | 'guide'
  | 'lobby'
  | 'game';
type Session = { gameId: string; playerId: string; name: string };
type Profile = { display_name: string; picture: string | null };
type EmoteName = 'laugh' | 'wow' | 'clap' | 'heart' | 'bluff' | 'cool' | 'fire' | 'crown' | 'eyes' | 'sweat' | 'shrug';
type DialogueName =
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
type AuthState =
  | { status: 'checking' }
  | { status: 'signed_out' }
  | { status: 'signing_in' }
  | { status: 'signed_in'; profile: Profile };

const R = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
const sym: Record<string, string> = { H: '♥', D: '♦', C: '♣', S: '♠' };
const ord = (n: number) => (n === 1 ? '1st' : n === 2 ? '2nd' : n === 3 ? '3rd' : `${n}th`);
const dialogueOptions: { name: DialogueName; label: string }[] = [
  { name: 'arre_bhai', label: 'Arre bhai, pakde gaye!' },
  { name: 'kya_scene', label: 'Kya scene hai, boss?' },
  { name: 'filmi_bluff', label: 'Full filmi bluff!' },
  { name: 'chai_break', label: 'Chai break ke baad challenge?' },
  { name: 'seedha_bol', label: 'Seedha bol, yaar!' },
  { name: 'wah_ustad', label: 'Wah, kya chaal hai!' },
  { name: 'dimaag_laga', label: 'Dimaag laga, dost!' },
  { name: 'jugaad_pro', label: 'Jugaad level: pro.' },
  { name: 'balle_balle', label: 'Balle balle, kya play!' },
  { name: 'shabaash_sher', label: 'Shabaash, sher!' },
  { name: 'rangey_haath', label: 'Oho, rangey haath!' },
  { name: 'kya_baat', label: 'Kya baat, kya baat!' },
  { name: 'boss_move', label: 'Boss move, ekdum!' },
  { name: 'scene_set', label: 'Aaj toh scene set hai!' },
];

function describeEvent(event: any, players: any[]) {
  const nameOf = (id: string) => players.find((player) => player.id === id)?.name || 'A player';
  switch (event.type) {
    case 'play':
      return { title: `${nameOf(event.player_id)} played ${event.count} ${event.count === 1 ? 'card' : 'cards'}`, detail: `Claiming ${event.rank}`, result: false };
    case 'skip':
    case 'timeout_skip':
      return { title: `${nameOf(event.player_id)} skipped`, detail: 'The table keeps moving.', result: false };
    case 'challenge':
      return {
        title: event.was_bluff ? 'BLUFF CAUGHT' : 'THE CLAIM WAS TRUE',
        detail: `${nameOf(event.challenger_id)} challenged ${nameOf(event.challenged_id)}. ${nameOf(event.loser_id)} takes ${event.pile} cards.${event.revealed_cards?.length ? ` Revealed: ${event.revealed_cards.join(' · ')}` : ''}`,
        result: true,
      };
    case 'close_round':
      return { title: `${nameOf(event.player_id)} closed the round`, detail: `${event.discarded_count} cards cleared from the pot.`, result: false };
    case 'return_to_contributor':
      return { title: 'BACK TO THE CONTRIBUTOR', detail: `${nameOf(event.player_id)} may add cards or close the round.`, result: false };
    case 'pause':
      return { title: 'TABLE ON HOLD', detail: `${nameOf(event.player_id)} paused the game.`, result: false };
    case 'resume':
      return { title: 'BACK IN PLAY', detail: `${nameOf(event.player_id)} resumed the game.`, result: false };
    case 'leave':
      return { title: `${nameOf(event.player_id)} LEFT THE TABLE`, detail: 'Their seat remains visible for the rest of the match.', result: false };
    case 'timeout_pause':
      return { title: 'TABLE ON HOLD', detail: 'The turn timed out. The game is paused.', result: false };
    case 'finished':
      return { title: 'THE TABLE IS SETTLED', detail: 'Final standings are in.', result: true };
    default:
      return null;
  }
}

function App() {
  const [screen, setScreen] = useState<Screen>('splash');
  const [load, setLoad] = useState(0);
  const [name, setName] = useState(localStorage.getItem('br_name') || '');
  const [code, setCode] = useState('');
  const [deckCount, setDeckCount] = useState(1);
  const [session, setSession] = useState<Session | null>(null);
  const [room, setRoom] = useState<any>(null);
  const [game, setGame] = useState<any>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [rank, setRank] = useState('A');
  const [error, setError] = useState('');
  const [authError, setAuthError] = useState('');
  const [auth, setAuth] = useState<AuthState>({ status: 'checking' });
  const [authIntent, setAuthIntent] = useState<'play' | 'history' | null>(null);
  const [returnScreen, setReturnScreen] = useState<Screen>('menu');
  const [busy, setBusy] = useState(false);
  const [pausePanel, setPausePanel] = useState<'menu' | 'options'>('menu');
  const [confirmQuit, setConfirmQuit] = useState(false);
  const [sendingEmote, setSendingEmote] = useState(false);
  const [sendingDialogue, setSendingDialogue] = useState(false);
  const [customDialogue, setCustomDialogue] = useState('');
  const [announcement, setAnnouncement] = useState<any>(null);
  const [sound, setSound] = useState(localStorage.getItem('br_sound') !== 'off');
  const [motion, setMotion] = useState(localStorage.getItem('br_motion') !== 'off');
  const [history, setHistory] = useState<any[]>([]);
  const signingIn = useRef(false);
  const pendingAction = useRef<(() => Promise<any>) | null>(null);
  const lastReactionAt = useRef(0);
  const latestGameEvent = game?.recent_events?.[game.recent_events.length - 1];

  useEffect(() => {
    if (!latestGameEvent?.at) return;
    setAnnouncement(latestGameEvent);
    const timer = window.setTimeout(() => setAnnouncement(null), 5200);
    return () => window.clearTimeout(timer);
  }, [latestGameEvent?.at]);

  useEffect(() => {
    let active = true;
    api.me().then(
      (profile: Profile) => {
        if (active) setAuth({ status: 'signed_in', profile });
      },
      (cause: unknown) => {
        if (!active) return;
        if (cause instanceof ApiError && cause.status === 401) {
          setAuth({ status: 'signed_out' });
        } else {
          setAuthError(
            cause instanceof Error
              ? `Unable to check your session: ${cause.message}`
              : 'Unable to check your session. Check your connection and retry.',
          );
        }
      },
    );
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!authIntent || auth.status === 'checking' || auth.status === 'signing_in') return;
    if (auth.status === 'signed_out') {
      setReturnScreen('menu');
      setScreen('signin');
      return;
    }
    const intent = authIntent;
    setAuthIntent(null);
    if (intent === 'play') {
      setScreen('play');
    } else {
      void openHistory();
    }
  }, [auth.status, authIntent]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setLoad((value) => {
        if (value >= 100) {
          window.clearInterval(timer);
          window.setTimeout(() => setScreen((current) => current === 'splash' ? 'menu' : current), 350);
          return 100;
        }
        return Math.min(100, value + 7);
      });
    }, 80);
    return () => window.clearInterval(timer);
  }, []);

  async function handleRequestError(cause: unknown, retry?: () => Promise<any>) {
    const message = cause instanceof Error ? cause.message : 'The request failed.';
    setError(message);
    if (cause instanceof ApiError && cause.status === 401) {
      pendingAction.current = retry || null;
      setAuth({ status: 'signed_out' });
      setAuthError('Your sign-in expired. Sign in again to continue.');
      setAuthIntent(null);
      setReturnScreen(screen);
      setScreen('signin');
    }
  }

  async function refresh() {
    if (!session) return;
    const nextRoom = await api.room(session.gameId);
    setRoom(nextRoom);
    if (nextRoom.status !== 'waiting') {
      const nextGame = await api.state(session.gameId, session.playerId);
      setGame(nextGame);
      if (nextRoom.status === 'playing' && screen === 'lobby') setScreen('game');
    }
  }

  useEffect(() => {
    if (!session || !['lobby', 'game'].includes(screen)) return;
    refresh().catch((cause) => void handleRequestError(cause));
    const interval = window.setInterval(() => {
      refresh().catch((cause) => void handleRequestError(cause));
    }, 700);
    return () => window.clearInterval(interval);
  }, [session?.gameId, session?.playerId, screen]);

  useEffect(() => {
    if (game?.paused) {
      setPausePanel('menu');
      setConfirmQuit(false);
    }
  }, [game?.paused]);

  async function run(action: () => Promise<any>) {
    setBusy(true);
    setError('');
    try {
      const result = await action();
      await refresh();
      return result;
    } catch (cause) {
      await handleRequestError(cause, action);
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  function saveName() {
    localStorage.setItem('br_name', name);
  }

  async function openHistory() {
    setError('');
    setScreen('history');
    setReturnScreen('history');
    try {
      setHistory(await api.history());
    } catch (cause) {
      await handleRequestError(cause, async () => {
        setScreen('history');
        setHistory(await api.history());
      });
    }
  }

  function requestEntry(intent: 'play' | 'history') {
    setAuthError('');
    setError('');
    setAuthIntent(intent);
    setReturnScreen('menu');
  }

  async function signedIn(profile: Profile) {
    setAuth({ status: 'signed_in', profile });
    setAuthError('');
    signingIn.current = false;
    const retry = pendingAction.current;
    pendingAction.current = null;
    if (retry) {
      setScreen(returnScreen);
      void run(retry);
      return;
    }
    if (!authIntent) setScreen(returnScreen);
  }

  async function retrySessionCheck() {
    setAuthError('');
    setAuth({ status: 'checking' });
    try {
      const profile = await api.me();
      setAuth({ status: 'signed_in', profile });
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        setAuth({ status: 'signed_out' });
      } else {
        setAuthError(cause instanceof Error ? cause.message : 'Unable to check your session.');
      }
    }
  }

  async function signOut() {
    setError('');
    try {
      await api.logout();
      setAuth({ status: 'signed_out' });
      setAuthIntent(null);
      setAuthError('');
      setSession(null);
      setRoom(null);
      setGame(null);
      setScreen('menu');
    } catch (cause) {
      await handleRequestError(cause);
    }
  }

  async function sendEmote(emote: EmoteName) {
    if (!session || sendingEmote || Date.now() - lastReactionAt.current < 650) return;
    lastReactionAt.current = Date.now();
    setSendingEmote(true);
    try {
      await api.emote(session.gameId, emote);
    } catch (cause) {
      await handleRequestError(cause);
    } finally {
      setSendingEmote(false);
    }
  }

  async function sendDialogue(message: { dialogue: DialogueName } | { custom_text: string }) {
    if (!session || sendingDialogue || Date.now() - lastReactionAt.current < 650) return;
    lastReactionAt.current = Date.now();
    setSendingDialogue(true);
    try {
      await api.dialogue(session.gameId, message);
      if ('custom_text' in message) setCustomDialogue('');
    } catch (cause) {
      await handleRequestError(cause);
    } finally {
      setSendingDialogue(false);
    }
  }

  async function leaveTable() {
    if (!session) return;
    setBusy(true);
    try {
      await api.leave(session.gameId);
      setSession(null);
      setRoom(null);
      setGame(null);
      setConfirmQuit(false);
      setScreen('menu');
    } catch (cause) {
      await handleRequestError(cause);
    } finally {
      setBusy(false);
    }
  }

  function accountChip() {
    if (auth.status === 'signed_in') {
      const profile = auth.profile;
      return (
        <div className="account-chip">
          {profile.picture ? (
            <img src={profile.picture} alt="" referrerPolicy="no-referrer" />
          ) : (
            <span className="account-initial">{profile.display_name.slice(0, 1).toUpperCase()}</span>
          )}
          <b>{profile.display_name}</b>
          <button onClick={() => void signOut()}>SIGN OUT</button>
        </div>
      );
    }
    if (auth.status === 'checking') {
      return <div className="account-chip" role="status">CHECKING SESSION…</div>;
    }
    return <button className="account-signin" onClick={() => requestEntry('play')}>SIGN IN</button>;
  }

  useRoyaleAudio(
    sound,
    screen === 'game' && game?.status === 'playing',
    game?.pile_size ?? 0,
    latestGameEvent?.at
      ? `${latestGameEvent.type}:${latestGameEvent.type === 'challenge' ? latestGameEvent.was_bluff ? 'bluff' : 'truth' : ''}:${latestGameEvent.at}`
      : '',
  );

  if (screen === 'splash') {
    return (
      <main className="splash">
        <div className="suits">♠ <i>♥</i> ♣ <i>♦</i></div>
        <h1>BLUFF <span>ROYALE</span></h1>
        <p>THE TABLE REMEMBERS EVERY LIE</p>
        <div className="loader"><b style={{ width: `${load}%` }} /></div>
        <small>SHUFFLING THE DECK · {load}%</small>
        <footer>© 2026 BLUFF ROYALE · ALL RIGHTS RESERVED</footer>
      </main>
    );
  }

  const back = <button className="back" onClick={() => setScreen('menu')}>← BACK</button>;

  if (screen === 'signin') {
    return (
      <main className="page signin-page">
        {back}
        <section className="signin-panel" aria-labelledby="signin-title">
          <span className="eyebrow">BLUFF ROYALE</span>
          <h2 id="signin-title">TAKE A SEAT</h2>
          <p>Sign in to create or join a private table and see your match history.</p>
          {auth.status === 'signing_in' && <p role="status">Signing in…</p>}
          <GoogleSignIn
            onSigningIn={() => {
              if (signingIn.current) return;
              signingIn.current = true;
              setAuth({ status: 'signing_in' });
              setAuthError('');
            }}
            onSignedIn={(profile) => void signedIn(profile)}
            onError={(message, confirmedSignedOut) => {
              signingIn.current = false;
              setAuth(confirmedSignedOut ? { status: 'signed_out' } : { status: 'checking' });
              setAuthError(message);
            }}
          />
          {authError && <div className="err" role="alert">{authError}</div>}
          {auth.status === 'checking' && authError && (
            <button className="dark" onClick={() => void retrySessionCheck()}>RETRY SESSION CHECK</button>
          )}
          <button className="signin-back" onClick={() => { setAuthIntent(null); setScreen('menu'); }}>
            BACK TO MENU
          </button>
        </section>
      </main>
    );
  }

  if (screen === 'menu') {
    return (
      <main className="menu">
        <div className="brand">
          <div className="menu-account">{accountChip()}</div>
          <span>♠</span>
          <h1>BLUFF<br /><b>ROYALE</b></h1>
          <p>Trust nobody. Remember everything.</p>
          {authError && <div className="auth-status" role="status">{authError}</div>}
          {auth.status === 'checking' && authError && <button className="account-signin" onClick={() => void retrySessionCheck()}>RETRY SESSION CHECK</button>}
        </div>
        <nav>
          <button onClick={() => requestEntry('play')}>▶ <span>PLAY</span></button>
          <button onClick={() => setScreen('rules')}>▤ <span>HOW TO PLAY</span></button>
          <button onClick={() => setScreen('guide')}>♛ <span>PLATFORM &amp; CREATOR</span></button>
          <button onClick={() => requestEntry('history')}>◷ <span>PREVIOUS GAMES</span></button>
          <button onClick={() => setScreen('options')}>⚙ <span>OPTIONS</span></button>
        </nav>
        <footer>BLUFF ROYALE · v0.7 · © 2026</footer>
      </main>
    );
  }

  if (screen === 'rules') {
    return (
      <main className="page">
        {back}{accountChip()}
        <section>
          <h2>HOW TO PLAY</h2>
          <div className="rules">
            <article><b>01</b><h3>OPEN THE ROUND</h3><p>The player holding A♠ opens the first round. A new-round starter chooses any rank and places one or more cards face-down.</p></article>
            <article><b>02</b><h3>KEEP THE CLAIM</h3><p>The claimed rank stays fixed for the whole round. On your turn add cards under that claim, call bluff on the latest contribution, or skip.</p></article>
            <article><b>03</b><h3>CALL THE LIE</h3><p>Only the latest contribution is revealed. If it was false, that player takes the entire accumulated pile. If it was true, the challenger takes everything.</p></article>
            <article><b>04</b><h3>SKIPS</h3><p>A new play resets skips. In a two-player round, the other player's skip returns control to the contributor, who may add cards or close the round. With 3+ active players, when every other active player skips, discard the pile and let the latest contributor open a new round.</p></article>
            <article><b>05</b><h3>FINISH</h3><p>Empty your hand to finish. Your final play remains challengeable. Finished players leave turn rotation and the remaining players continue for positions.</p></article>
            <article><b>40</b><h3>SECONDS</h3><p>Every turn has 40 seconds. Ordinary active-turn timeouts become skips. If a new-round starter times out before playing, or control returns to a contributor in a two-player round, the game pauses instead of choosing cards for them.</p></article>
          </div>
        </section>
      </main>
    );
  }

  if (screen === 'guide') {
    return (
      <main className="page">
        {back}{accountChip()}
        <section className="platform-guide">
          <span className="eyebrow">WELCOME TO THE TABLE</span>
          <h2>YOUR GUIDE</h2>
          <div className="guide-steps">
            <article><b>01 · TAKE A SEAT</b><p>Sign in, choose your table name, and create a private room or join a friend's room code.</p></article>
            <article><b>02 · PICK YOUR DECKS</b><p>The host can choose one, two, or three standard decks when creating a room. Everyone gets a bigger hand as decks increase.</p></article>
            <article><b>03 · PLAY THE TABLE</b><p>The A♠ holder opens the first round. Make your claim, read the table, call a bluff, and be the first to empty your hand.</p></article>
            <article><b>04 · KEEP IT ROYALE</b><p>Use reactions and table talk, watch the turn timer, and check the leaderboard when the match is settled.</p></article>
          </div>
          <div className="creator-card">
            <span className="eyebrow">BUILT BY</span>
            <h3>Archit Dogra</h3>
            <a href="mailto:architdogra07@gmail.com">architdogra07@gmail.com</a>
            <a href="https://github.com/Archit0720" target="_blank" rel="noreferrer">GitHub · @Archit0720</a>
          </div>
        </section>
      </main>
    );
  }

  if (screen === 'options') {
    return (
      <main className="page">
        {back}{accountChip()}
        <section className="settings">
          <h2>OPTIONS</h2>
          <label>PLAYER NAME<input value={name} onChange={(event) => setName(event.target.value)} onBlur={saveName} /></label>
          <div><span>SOUND EFFECTS<small>Interface and table sounds</small></span><button className={sound ? 'toggle on' : 'toggle'} onClick={() => { setSound(!sound); localStorage.setItem('br_sound', sound ? 'off' : 'on'); }}>{sound ? 'ON' : 'OFF'}</button></div>
          <div><span>TABLE ANIMATIONS<small>Glow and card motion</small></span><button className={motion ? 'toggle on' : 'toggle'} onClick={() => { setMotion(!motion); localStorage.setItem('br_motion', motion ? 'off' : 'on'); }}>{motion ? 'ON' : 'OFF'}</button></div>
        </section>
      </main>
    );
  }

  if (screen === 'history') {
    return (
      <main className="page">
        {back}{accountChip()}
        <section>
          <h2>MY MATCHES</h2>
          {error && <div className="err" role="alert">{error}</div>}
          {history.length ? history.map((match: any, index: number) => (
            <div className="history" key={index}>
              <b>ROOM {match.room_code}</b>
              <span>{new Date(match.finished_at).toLocaleString()}</span>
              <div>{match.standings.map((id: string, place: number) => (
                <em key={id}>{ord(place + 1)} · {match.players.find((player: any) => player.id === id)?.name}</em>
              ))}</div>
            </div>
          )) : !error && <div className="empty">No completed matches found for your account.</div>}
        </section>
      </main>
    );
  }

  if (screen === 'play') {
    return (
      <main className="page">
        {back}{accountChip()}
        <section className="join">
          <h2>CREATE OR JOIN TABLE</h2>
          <label>PLAYER NAME<input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Your table name" /></label>
          <label className="deck-select">NUMBER OF DECKS
            <select value={deckCount} onChange={(event) => setDeckCount(Number(event.target.value))}>
              <option value={1}>1 deck · Standard</option>
              <option value={2}>2 decks · Bigger hands</option>
              <option value={3}>3 decks · Maximum chaos</option>
            </select>
            <small>For rooms you create only. Joining uses the host's deck choice; one deck is the default.</small>
          </label>
          <button className="gold" disabled={!name.trim() || busy} onClick={() => void run(async () => {
            saveName();
            const created = await api.create(name, deckCount);
            setSession({ gameId: created.game_id, playerId: created.player_id, name: created.player_name });
            setScreen('lobby');
          })}>CREATE PRIVATE TABLE</button>
          <div className="or">OR JOIN A TABLE</div>
          <input className="code" value={code} maxLength={5} onChange={(event) => setCode(event.target.value.toUpperCase())} placeholder="ROOM CODE" />
          <button className="dark" disabled={!name.trim() || code.length < 5 || busy} onClick={() => void run(async () => {
            saveName();
            const joined = await api.join(code, name);
            setSession({ gameId: joined.game_id, playerId: joined.player_id, name: joined.player_name });
            setScreen('lobby');
          })}>JOIN TABLE</button>
          {error && <div className="err" role="alert">{error}</div>}
        </section>
      </main>
    );
  }

  if (screen === 'lobby' && session) {
    return (
      <main className="page casino">
        {back}{accountChip()}
        <section className="lobby">
          <span className="eyebrow">PRIVATE TABLE</span>
          <h2>{session.gameId}</h2>
          <p>Invite players with this room code</p>
          <div className="seats">
            {room?.players.map((player: any, index: number) => (
              <div className="seat" key={player.id}>
                <div className="seat-avatar">{player.picture ? <img src={player.picture} alt="" referrerPolicy="no-referrer" /> : player.name[0]?.toUpperCase()}</div>
                <b>{player.name}</b>
                <small>{player.on_hold ? 'ON HOLD' : player.presence === 'left' ? 'LEFT' : index === 0 ? 'HOST' : 'READY'}</small>
              </div>
            ))}
            {Array.from({ length: Math.max(0, 6 - (room?.players.length || 0)) }).map((_, index) => (
              <div className="seat vacant" key={index}><div>+</div><b>OPEN SEAT</b><small>WAITING</small></div>
            ))}
          </div>
          {room?.is_host ? (
            <button className="gold" disabled={(room?.players.length || 0) < 2 || busy} onClick={() => void run(() => api.start(session.gameId))}>
              {busy ? 'STARTING…' : `START GAME · ${room?.deck_count || 1} ${(room?.deck_count || 1) === 1 ? 'DECK' : 'DECKS'}`}
            </button>
          ) : (
            <p className="waiting-host" role="status">WAITING FOR THE HOST TO START</p>
          )}
          <small>{room?.deck_count || 1} {(room?.deck_count || 1) === 1 ? 'deck' : 'decks'} · A♠ decides who opens the first round</small>
          {error && <div className="err" role="alert">{error}</div>}
        </section>
      </main>
    );
  }

  if (screen === 'game' && session && game) {
    if (game.status === 'finished') {
      return (
        <main className="page casino">
          {accountChip()}
          <section className="results">
            <span className="eyebrow">FINAL TABLE</span><h2>STANDINGS</h2>
            {game.finishing_order.map((id: string, index: number) => {
              const player = game.players.find((item: any) => item.id === id);
              return (
                <article className={`leader-row place-${index + 1}`} key={id}>
                  <b className="leader-rank">{index < 3 ? ['♛', '♜', '♜'][index] : ord(index + 1)}</b>
                  <div className="leader-avatar">{player?.picture ? <img src={player.picture} alt="" referrerPolicy="no-referrer" /> : player?.name?.slice(0, 1).toUpperCase()}</div>
                  <span>{player?.name}</span>
                  {id === session.playerId && <em>YOU</em>}
                  {index === 0 && <strong>CHAMPION</strong>}
                </article>
              );
            })}
            <p className="leader-caption">The cards have spoken. The table remembers.</p>
            <button className="gold" onClick={() => { setSession(null); setRoom(null); setGame(null); setScreen('menu'); }}>RETURN TO MENU</button>
          </section>
        </main>
      );
    }

    const turn = game.current_player_id === session.playerId;
    const starter = turn && game.current_rank === null;
    const emoteOptions: { name: EmoteName; symbol: string; label: string }[] = [
      { name: 'laugh', symbol: '😂', label: 'Laugh' },
      { name: 'wow', symbol: '😮', label: 'Wow' },
      { name: 'clap', symbol: '👏', label: 'Clap' },
      { name: 'heart', symbol: '❤️', label: 'Heart' },
      { name: 'bluff', symbol: '🤥', label: 'Bluff' },
      { name: 'cool', symbol: '😎', label: 'Cool' },
      { name: 'fire', symbol: '🔥', label: 'Fire' },
      { name: 'crown', symbol: '👑', label: 'Crown' },
      { name: 'eyes', symbol: '👀', label: 'Eyes' },
      { name: 'sweat', symbol: '😅', label: 'Nervous' },
      { name: 'shrug', symbol: '🤷', label: 'Shrug' },
    ];
    const recentEmotes = (room?.recent_emotes || [])
      .filter((item: any) => Date.now() / 1000 - item.created_at < 5)
      .slice(0, 4)
      .reverse();
    const tableAnnouncement = announcement && describeEvent(announcement, game.players);
    const toggleCard = (index: number) => setSelected((current) =>
      current.includes(index) ? current.filter((item) => item !== index) : [...current, index],
    );
    return (
      <main className={`game ${motion ? 'motion' : ''}`}>
        <header>
          <div className="smallbrand">♠ BLUFF ROYALE</div>
          <div>TABLE <b>{session.gameId}</b></div>
          {accountChip()}
          <button onClick={() => void run(() => game.paused ? api.resume(session.gameId, session.playerId) : api.pause(session.gameId, session.playerId))}>{game.paused ? '▶ RESUME' : 'Ⅱ PAUSE'}</button>
        </header>
        <RoyaleTable game={game} playerId={session.playerId} motion={motion} />
        {tableAnnouncement && (
          <div className={`table-announcement${tableAnnouncement.result ? ' result' : ''}`} role="status" aria-live="polite">
            <b>{tableAnnouncement.title}</b><span>{tableAnnouncement.detail}</span>
          </div>
        )}
        {recentEmotes.length > 0 && (
          <div className="emote-feed" aria-live="polite">
            {recentEmotes.map((item: any) => (
              <span key={`${item.player_id}-${item.created_at}`} className={item.kind === 'dialogue' ? 'dialogue-reaction' : item.kind === 'system' ? 'system-reaction' : 'emote-reaction'}>
                {item.kind === 'dialogue'
                  ? dialogueOptions.find((option) => option.name === item.dialogue)?.label
                  : item.kind === 'custom'
                    ? item.custom_text
                  : item.kind === 'system' && item.system_event === 'leave'
                    ? 'LEFT THE TABLE'
                    : emoteOptions.find((option) => option.name === item.emote)?.symbol}
                <small>{game.players.find((player: any) => player.id === item.player_id)?.name || 'Player'}</small>
              </span>
            ))}
          </div>
        )}
        <section className="hud">
          <div className="message">
            {game.paused ? <><b>TABLE ON HOLD</b><span>{game.players.find((player: any) => player.id === game.paused_by)?.name || 'The table'} paused the game.</span></> : starter ? <><b>YOU OPEN THE ROUND</b><span>Choose the rank you want everyone to claim.</span></> : turn ? <><b>YOUR MOVE</b><span>Play, challenge the latest claim, or skip.</span></> : <><b>{game.players.find((player: any) => player.id === game.current_player_id)?.name}'S TURN</b><span>Watch the table. Remember every claim.</span></>}
          </div>
          {starter && <div className="rankbar">{R.map((item) => <button key={item} className={item === rank ? 'selected' : ''} onClick={() => setRank(item)}>{item}</button>)}</div>}
          <div className="cards">{game.your_hand.map((card: string, index: number) => {
            const suit = card.slice(-1);
            return <button key={`${card}-${index}`} disabled={!turn || game.paused} onClick={() => toggleCard(index)} className={`${'HD'.includes(suit) ? 'red' : ''} ${selected.includes(index) ? 'picked' : ''}`}><span>{card.slice(0, -1)}</span><b>{sym[suit]}</b></button>;
          })}</div>
          <div className="actions">
            <button className="playbtn" disabled={!turn || game.paused || !selected.length} onClick={() => void run(async () => {
              await api.play(session.gameId, session.playerId, selected, starter ? rank : undefined);
              setSelected([]);
            })}>PLAY {selected.length || ''}</button>
            {game.available_actions.includes('challenge') && <button className="bluff" disabled={game.paused} onClick={() => void run(() => api.challenge(session.gameId, session.playerId))}>CALL BLUFF</button>}
            {game.available_actions.includes('skip') && <button className="skip" disabled={game.paused} onClick={() => void run(() => api.skip(session.gameId, session.playerId))}>SKIP</button>}
            {game.available_actions.includes('close_round') && <button className="skip" disabled={game.paused} onClick={() => void run(() => api.closeRound(session.gameId, session.playerId))}>CLOSE ROUND</button>}
          </div>
          <div className="emote-bar" aria-label="Send an emote">
            <span>EMOTES</span>
            {emoteOptions.map((option) => (
              <button
                key={option.name}
                type="button"
                aria-label={`Send ${option.label} emote`}
                title={option.label}
                disabled={sendingEmote || game.status !== 'playing' || game.paused}
                onClick={() => void sendEmote(option.name)}
              >
                {option.symbol}
              </button>
            ))}
          </div>
          <div className="dialogue-bar" aria-label="Send table talk">
            <span>TABLE TALK</span>
            <div className="dialogue-presets">
              {dialogueOptions.map((option) => (
                <button key={option.name} type="button" disabled={sendingDialogue || game.paused} onClick={() => void sendDialogue({ dialogue: option.name })}>{option.label}</button>
              ))}
            </div>
            <form className="custom-dialogue" onSubmit={(event) => {
              event.preventDefault();
              const text = customDialogue.trim();
              if (text) void sendDialogue({ custom_text: text });
            }}>
              <input
                aria-label="Write custom table talk"
                placeholder="Write your own line…"
                maxLength={120}
                value={customDialogue}
                disabled={sendingDialogue || game.paused}
                onChange={(event) => setCustomDialogue(event.target.value)}
              />
              <button type="submit" disabled={sendingDialogue || game.paused || !customDialogue.trim()}>SEND</button>
              <small>{customDialogue.length}/120</small>
            </form>
          </div>
          {error && <div className="err" role="alert">{error}</div>}
        </section>
        {game.paused && (
          <div className="pause">
            {confirmQuit ? (
              <article className="pause-card">
                <h2>QUIT TO MENU?</h2>
                <p>Your seat stays visible as LEFT. Turns will continue using the normal timeout rules.</p>
                <button className="gold" disabled={busy} onClick={() => void leaveTable()}>{busy ? 'LEAVING…' : 'LEAVE TABLE'}</button>
                <button className="dark" onClick={() => setConfirmQuit(false)}>CANCEL</button>
              </article>
            ) : pausePanel === 'options' ? (
              <article className="pause-card pause-options">
                <span>Ⅱ TABLE PAUSED</span>
                <h2>OPTIONS</h2>
                <label>PLAYER NAME<input value={name} onChange={(event) => setName(event.target.value)} onBlur={saveName} /></label>
                <div><span>SOUND EFFECTS</span><button className={sound ? 'toggle on' : 'toggle'} onClick={() => { setSound(!sound); localStorage.setItem('br_sound', sound ? 'off' : 'on'); }}>{sound ? 'ON' : 'OFF'}</button></div>
                <div><span>TABLE ANIMATIONS</span><button className={motion ? 'toggle on' : 'toggle'} onClick={() => { setMotion(!motion); localStorage.setItem('br_motion', motion ? 'off' : 'on'); }}>{motion ? 'ON' : 'OFF'}</button></div>
                <button className="dark" onClick={() => setPausePanel('menu')}>BACK TO PAUSE MENU</button>
              </article>
            ) : (
              <article className="pause-card">
                <div>Ⅱ</div>
                <h2>TABLE PAUSED</h2>
                <p>{game.paused_by === 'system' ? `Turn clock frozen at ${game.turn_seconds_left}s` : `${game.players.find((player: any) => player.id === game.paused_by)?.name || 'A player'} put the table on hold.`}</p>
                {(game.paused_by === session.playerId || game.paused_by === 'system' || room?.is_host || game.players.find((player: any) => player.id === game.paused_by)?.presence === 'left') ? (
                  <button className="gold" onClick={() => void run(() => api.resume(session.gameId, session.playerId))}>RESUME GAME</button>
                ) : (
                  <p className="waiting-host" role="status">WAITING FOR THE HOST OR PAUSING PLAYER</p>
                )}
                <button className="dark" onClick={() => setPausePanel('options')}>OPTIONS</button>
                <button className="quit-button" onClick={() => setConfirmQuit(true)}>QUIT TO MENU</button>
              </article>
            )}
          </div>
        )}
      </main>
    );
  }
  return <main className="splash"><h1>CONNECTING…</h1></main>;
}

createRoot(document.getElementById('root')!).render(<App />);
