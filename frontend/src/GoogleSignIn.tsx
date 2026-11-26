import { useEffect, useRef, useState } from 'react';
import { api } from './api';

type GoogleCredentialResponse = { credential: string };
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
  onSignedIn,
  onError,
}: {
  onSignedIn: () => void;
  onError: (message: string) => void;
}) {
  const button = useRef<HTMLDivElement>(null);
  const handlers = useRef({ onSignedIn, onError });
  const [message, setMessage] = useState('');
  handlers.current = { onSignedIn, onError };

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
            try {
              await api.login(credential, nonce);
              handlers.current.onSignedIn();
            } catch (error) {
              const text = error instanceof Error ? error.message : 'Google sign-in failed.';
              handlers.current.onError(text);
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
        handlers.current.onError(text);
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
        handlers.current.onError(text);
      }, 10000);
    }
    return () => {
      cancelled = true;
      if (interval !== undefined) window.clearInterval(interval);
      if (timeout !== undefined) window.clearTimeout(timeout);
    };
  }, []);

  return (
    <div className="google-signin">
      <div ref={button} />
      {message && <small role="status">{message}</small>}
    </div>
  );
}
