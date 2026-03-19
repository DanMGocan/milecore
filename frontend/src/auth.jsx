import { useState } from 'react';
import { useAuth } from './AuthContext';

export function AuthPage({ onSuccess }) {
    const { login, signup } = useAuth();
    const [tab, setTab] = useState('signin');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    // Sign In fields
    const [signInEmail, setSignInEmail] = useState('');
    const [signInPassword, setSignInPassword] = useState('');

    // Sign Up fields
    const [signUpName, setSignUpName] = useState('');
    const [signUpEmail, setSignUpEmail] = useState('');
    const [signUpPassword, setSignUpPassword] = useState('');

    const handleSignIn = async (e) => {
        e.preventDefault();
        setError('');
        if (!signInEmail.trim() || !signInPassword) {
            setError('Please fill in all fields.');
            return;
        }
        setLoading(true);
        try {
            await login(signInEmail.trim(), signInPassword);
            if (onSuccess) onSuccess();
        } catch (err) {
            setError(err.message || 'Login failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleSignUp = async (e) => {
        e.preventDefault();
        setError('');
        if (!signUpName.trim() || !signUpEmail.trim() || !signUpPassword) {
            setError('Please fill in all fields.');
            return;
        }
        if (signUpPassword.length < 8) {
            setError('Password must be at least 8 characters.');
            return;
        }
        setLoading(true);
        try {
            await signup(signUpEmail.trim(), signUpPassword, signUpName.trim());
            if (onSuccess) onSuccess();
        } catch (err) {
            setError(err.message || 'Signup failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSignIn = () => {
        window.location.href = '/api/auth/google';
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-logo">TrueCore.cloud</div>

                <div className="auth-tabs">
                    <button
                        className={`auth-tab${tab === 'signin' ? ' active' : ''}`}
                        onClick={() => { setTab('signin'); setError(''); }}
                        type="button"
                    >
                        Sign In
                    </button>
                    <button
                        className={`auth-tab${tab === 'signup' ? ' active' : ''}`}
                        onClick={() => { setTab('signup'); setError(''); }}
                        type="button"
                    >
                        Sign Up
                    </button>
                </div>

                {error && <div className="auth-error">{error}</div>}

                {tab === 'signin' && (
                    <form onSubmit={handleSignIn} noValidate>
                        <div className="auth-field">
                            <label htmlFor="signin-email">Email</label>
                            <input
                                id="signin-email"
                                type="email"
                                className="form-input"
                                placeholder="you@example.com"
                                value={signInEmail}
                                onChange={(e) => setSignInEmail(e.target.value)}
                                autoComplete="email"
                                disabled={loading}
                            />
                        </div>
                        <div className="auth-field">
                            <label htmlFor="signin-password">Password</label>
                            <input
                                id="signin-password"
                                type="password"
                                className="form-input"
                                placeholder="Enter your password"
                                value={signInPassword}
                                onChange={(e) => setSignInPassword(e.target.value)}
                                autoComplete="current-password"
                                disabled={loading}
                            />
                        </div>
                        <button
                            type="submit"
                            className="btn btn-primary auth-submit-btn"
                            disabled={loading}
                        >
                            {loading ? 'Signing in...' : 'Sign In'}
                        </button>

                        <div className="auth-divider">
                            <span>or</span>
                        </div>

                        <button
                            type="button"
                            className="btn auth-google-btn"
                            onClick={handleGoogleSignIn}
                            disabled={loading}
                        >
                            <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
                                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                            </svg>
                            Sign in with Google
                        </button>
                    </form>
                )}

                {tab === 'signup' && (
                    <form onSubmit={handleSignUp} noValidate>
                        <div className="auth-field">
                            <label htmlFor="signup-name">Display Name</label>
                            <input
                                id="signup-name"
                                type="text"
                                className="form-input"
                                placeholder="Your name"
                                value={signUpName}
                                onChange={(e) => setSignUpName(e.target.value)}
                                autoComplete="name"
                                disabled={loading}
                            />
                        </div>
                        <div className="auth-field">
                            <label htmlFor="signup-email">Email</label>
                            <input
                                id="signup-email"
                                type="email"
                                className="form-input"
                                placeholder="you@example.com"
                                value={signUpEmail}
                                onChange={(e) => setSignUpEmail(e.target.value)}
                                autoComplete="email"
                                disabled={loading}
                            />
                        </div>
                        <div className="auth-field">
                            <label htmlFor="signup-password">Password</label>
                            <input
                                id="signup-password"
                                type="password"
                                className="form-input"
                                placeholder="At least 8 characters"
                                value={signUpPassword}
                                onChange={(e) => setSignUpPassword(e.target.value)}
                                autoComplete="new-password"
                                disabled={loading}
                            />
                        </div>
                        <button
                            type="submit"
                            className="btn btn-primary auth-submit-btn"
                            disabled={loading}
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                        </button>
                    </form>
                )}
            </div>

            <style>{`
                .auth-page {
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--bg-primary);
                    padding: 20px;
                }

                .auth-card {
                    width: 100%;
                    max-width: 400px;
                    background: var(--bg-secondary);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-lg);
                    padding: 36px 32px 32px;
                    box-shadow: var(--shadow-lg);
                    animation: scaleIn 0.25s ease;
                }

                .auth-logo {
                    text-align: center;
                    font-size: 24px;
                    font-weight: 700;
                    background: var(--gradient-accent);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin-bottom: 28px;
                    letter-spacing: -0.5px;
                }

                .auth-tabs {
                    display: flex;
                    gap: 0;
                    margin-bottom: 24px;
                    border-bottom: 1px solid var(--border);
                }

                .auth-tab {
                    flex: 1;
                    padding: 10px 0;
                    background: none;
                    border: none;
                    border-bottom: 2px solid transparent;
                    color: var(--text-secondary);
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: color var(--transition-fast), border-color var(--transition-fast);
                }

                .auth-tab:hover {
                    color: var(--text-primary);
                }

                .auth-tab.active {
                    color: var(--accent);
                    border-bottom-color: var(--accent);
                }

                .auth-error {
                    background: rgba(248, 113, 113, 0.1);
                    border: 1px solid rgba(248, 113, 113, 0.3);
                    color: var(--error);
                    padding: 10px 14px;
                    border-radius: var(--radius);
                    font-size: 13px;
                    margin-bottom: 16px;
                    line-height: 1.4;
                }

                .auth-field {
                    margin-bottom: 16px;
                }

                .auth-field label {
                    display: block;
                    font-size: 13px;
                    font-weight: 500;
                    color: var(--text-secondary);
                    margin-bottom: 6px;
                }

                .auth-submit-btn {
                    width: 100%;
                    padding: 10px 16px;
                    font-size: 14px;
                    margin-top: 4px;
                }

                .auth-divider {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin: 20px 0;
                    color: var(--text-muted);
                    font-size: 12px;
                }

                .auth-divider::before,
                .auth-divider::after {
                    content: '';
                    flex: 1;
                    height: 1px;
                    background: var(--border);
                }

                .auth-google-btn {
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    padding: 10px 16px;
                    font-size: 14px;
                    background: transparent;
                    border: 1px solid var(--border);
                    color: var(--text-primary);
                    transition: background var(--transition-fast), border-color var(--transition-fast);
                }

                .auth-google-btn:hover {
                    background: var(--bg-tertiary);
                    border-color: var(--text-muted);
                }
            `}</style>
        </div>
    );
}
