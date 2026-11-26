import { useEffect, useState } from 'react';
import { api } from './api';
import GoogleSignIn from './GoogleSignIn';
import './auth-controls.css';

export default function AuthControls() {
  const [signedIn, setSignedIn] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.me()
      .then(() => setSignedIn(true))
      .catch((cause: Error) => {
        if (cause.message !== 'Sign-in is required.') setError(cause.message);
      });
  }, []);

  async function signOut() {
    try {
      await api.logout();
      window.location.reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Sign-out failed.');
    }
  }

  return (
    <div className="auth-controls">
      {signedIn ? (
        <button className="auth-button" onClick={signOut}>SIGN OUT</button>
      ) : (
        <GoogleSignIn
          onSignedIn={() => {
            setSignedIn(true);
            setError('');
          }}
          onError={setError}
        />
      )}
      {error && <small role="alert">{error}</small>}
    </div>
  );
}
