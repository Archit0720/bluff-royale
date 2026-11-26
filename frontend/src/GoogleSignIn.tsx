import { useEffect, useRef, useState } from 'react';
import { ApiError, api } from './api';

type GoogleCredentialResponse = { credential: string };
type Profile = { display_name: string; picture: string | null };
type GoogleIdentity = {
  accounts: {
    id: {
      initialize: (options: {
        client_id: string;
        nonce: string;
        callback: (response: GoogleCredentialResponse) => void;
      }) => void;
      renderButton: (parent: HTMLElement, options: { theme: string; size: string }) => void;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentity;
  }
}

export default function GoogleSignIn({
  onSigningIn,
  onSignedIn,
  onError,
}: {
  onSigningIn: () => void;
  onSignedIn: (profile: Profile) => void;
  onError: (message: string, confirmedSignedOut: boolean) => void;
}) {
  const button = useRef<HTMLDivElement>(null);
  const activeLogin = useRef(false);
  const handlers = useRef({ onSigningIn, onSignedIn, onError });
  const [message, setMessage] = useState('');
  const [attempt, setAttempt] = useState(0);
  handlers.current = { onSigningIn, onSignedIn, onError };

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setMessage('Set VITE_GOOGLE_CLIENT_ID to enable sign-in.');
      return;
    }

    let cancelled = false;
    let interval: number | undefined;
    let timeout: number | undefined;

    const initialize = async (google: GoogleIdentity) => {
      try {
        const { nonce } = await api.nonce();
        if (cancelled || !button.current) return;
        google.accounts.id.initialize({
          client_id: clientId,
          nonce,
          callback: async ({ credential }) => {
            if (activeLogin.current) return;
            activeLogin.current = true;
            handlers.current.onSigningIn();
            try {
              await api.login(credential, nonce);
              const profile = await api.me();
              handlers.current.onSignedIn(profile);
            } catch (error) {
              const text = error instanceof Error ? error.message : 'Google sign-in failed.';
              activeLogin.current = false;
              handlers.current.onError(
                text,
                error instanceof ApiError && error.status === 401,
              );
              void initialize(google);
            }
          },
        });
        button.current.replaceChildren();
        google.accounts.id.renderButton(button.current, { theme: 'filled_black', size: 'large' });
        setMessage('');
      } catch (error) {
        if (cancelled) return;
        const text = error instanceof Error ? error.message : 'Unable to start Google sign-in.';
        setMessage(text);
        handlers.current.onError(text, false);
      }
    };

    const waitForGoogle = () => {
      if (window.google) {
        if (interval !== undefined) window.clearInterval(interval);
        if (timeout !== undefined) window.clearTimeout(timeout);
        void initialize(window.google);
      }
    };

    waitForGoogle();
    if (!window.google) {
      interval = window.setInterval(waitForGoogle, 100);
      timeout = window.setTimeout(() => {
        if (window.google || cancelled) return;
        if (interval !== undefined) window.clearInterval(interval);
        const text = 'Google sign-in did not load. Check the network connection and try again.';
        setMessage(text);
        handlers.current.onError(text, false);
      }, 10000);
    }
    return () => {
      cancelled = true;
      if (interval !== undefined) window.clearInterval(interval);
      if (timeout !== undefined) window.clearTimeout(timeout);
    };
  }, [attempt]);

  return (
    <div className="google-signin">
      <div ref={button} />
      {message && <small role="status">{message}</small>}
      {message && (
        <button className="google-retry" onClick={() => {
          setMessage('');
          setAttempt((value) => value + 1);
        }}>
          RETRY GOOGLE SIGN-IN
        </button>
      )}
    </div>
  );
}
