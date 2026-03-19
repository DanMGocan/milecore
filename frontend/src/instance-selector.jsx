import { useState } from 'react';
import { useAuth } from './AuthContext';

export function InstanceSelector({ onInstanceSelected }) {
    const { user, instances, selectInstance, refreshInstances, logout } = useAuth();

    const [createOpen, setCreateOpen] = useState(false);
    const [createName, setCreateName] = useState('');
    const [createSlug, setCreateSlug] = useState('');
    const [createLoading, setCreateLoading] = useState(false);
    const [createError, setCreateError] = useState('');

    const [joinLoading, setJoinLoading] = useState(false);
    const [joinMessage, setJoinMessage] = useState('');
    const [joinIsError, setJoinIsError] = useState(false);

    const [enteringId, setEnteringId] = useState(null);

    const handleEnter = async (id) => {
        setEnteringId(id);
        try {
            await selectInstance(id);
            if (onInstanceSelected) onInstanceSelected();
        } catch {
            setEnteringId(null);
        }
    };

    const handleCreateInstance = async (e) => {
        e.preventDefault();
        setCreateError('');
        if (!createName.trim()) {
            setCreateError('Instance name is required.');
            return;
        }
        if (!createSlug.trim()) {
            setCreateError('Slug is required.');
            return;
        }
        if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(createSlug.trim())) {
            setCreateError('Slug must be lowercase letters, numbers, and hyphens only.');
            return;
        }
        setCreateLoading(true);
        try {
            const res = await fetch('/api/instances', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: createName.trim(), slug: createSlug.trim() }),
                credentials: 'include',
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Failed to create instance.');
            }
            setCreateName('');
            setCreateSlug('');
            setCreateOpen(false);
            await refreshInstances();
        } catch (err) {
            setCreateError(err.message);
        } finally {
            setCreateLoading(false);
        }
    };

    const handleJoin = async () => {
        setJoinLoading(true);
        setJoinMessage('');
        setJoinIsError(false);
        try {
            const res = await fetch('/api/instances/join', {
                method: 'POST',
                credentials: 'include',
            });
            const data = await res.json();
            if (res.ok && data.joined) {
                setJoinMessage('Invitation accepted! The instance has been added to your list.');
                setJoinIsError(false);
                await refreshInstances();
            } else {
                setJoinMessage(
                    data.detail ||
                    'No pending invitation found. Ask the instance owner to invite you.'
                );
                setJoinIsError(true);
            }
        } catch {
            setJoinMessage('Something went wrong. Please try again.');
            setJoinIsError(true);
        } finally {
            setJoinLoading(false);
        }
    };

    const handleNameChange = (value) => {
        setCreateName(value);
        // Auto-generate slug from name if slug hasn't been manually edited
        const autoSlug = value
            .toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '');
        setCreateSlug(autoSlug);
    };

    const roleBadgeClass = (role) => {
        if (role === 'owner') return 'instance-role instance-role-owner';
        if (role === 'admin') return 'instance-role instance-role-admin';
        return 'instance-role';
    };

    return (
        <div className="instance-selector">
            <div className="instance-selector-card">
                <div className="auth-logo">TrueCore.cloud</div>

                <p className="instance-greeting">
                    Welcome, <strong>{user?.display_name || user?.email || 'User'}</strong>
                </p>

                {/* Your Instances */}
                <section className="instance-section">
                    <h3 className="instance-section-title">Your Instances</h3>
                    {instances.length > 0 ? (
                        <div className="instance-list">
                            {instances.map((inst) => (
                                <div key={inst.id} className="instance-item">
                                    <div className="instance-item-info">
                                        <span className="instance-item-name">{inst.name}</span>
                                        <span className={roleBadgeClass(inst.role)}>{inst.role}</span>
                                    </div>
                                    <button
                                        className="btn btn-primary instance-enter-btn"
                                        onClick={() => handleEnter(inst.id)}
                                        disabled={enteringId !== null}
                                    >
                                        {enteringId === inst.id ? 'Entering...' : 'Enter'}
                                    </button>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="instance-empty">You don't have any instances yet.</p>
                    )}
                </section>

                {/* Create New Instance */}
                <section className="instance-section">
                    <h3 className="instance-section-title">Create New Instance</h3>
                    {!createOpen ? (
                        <button
                            className="btn instance-expand-btn"
                            onClick={() => setCreateOpen(true)}
                            type="button"
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                <line x1="12" y1="5" x2="12" y2="19" />
                                <line x1="5" y1="12" x2="19" y2="12" />
                            </svg>
                            New Instance
                        </button>
                    ) : (
                        <form className="instance-create-form" onSubmit={handleCreateInstance} noValidate>
                            {createError && <div className="auth-error">{createError}</div>}
                            <div className="auth-field">
                                <label htmlFor="instance-name">Instance Name</label>
                                <input
                                    id="instance-name"
                                    type="text"
                                    className="form-input"
                                    placeholder="My Company"
                                    value={createName}
                                    onChange={(e) => handleNameChange(e.target.value)}
                                    disabled={createLoading}
                                />
                            </div>
                            <div className="auth-field">
                                <label htmlFor="instance-slug">Slug</label>
                                <input
                                    id="instance-slug"
                                    type="text"
                                    className="form-input"
                                    placeholder="my-company"
                                    value={createSlug}
                                    onChange={(e) => setCreateSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                                    disabled={createLoading}
                                />
                                <span className="instance-slug-hint">
                                    Lowercase letters, numbers, and hyphens only
                                </span>
                            </div>
                            <div className="instance-create-actions">
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={createLoading}
                                >
                                    {createLoading ? 'Creating...' : 'Create Instance'}
                                </button>
                                <button
                                    type="button"
                                    className="btn"
                                    onClick={() => { setCreateOpen(false); setCreateError(''); }}
                                    disabled={createLoading}
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    )}
                </section>

                {/* Join an Instance */}
                <section className="instance-section">
                    <h3 className="instance-section-title">Join an Instance</h3>
                    <button
                        className="btn instance-join-btn"
                        onClick={handleJoin}
                        disabled={joinLoading}
                        type="button"
                    >
                        {joinLoading ? 'Checking...' : 'Check for Invitations'}
                    </button>
                    {joinMessage && (
                        <div className={`instance-join-message${joinIsError ? ' instance-join-error' : ' instance-join-success'}`}>
                            {joinMessage}
                        </div>
                    )}
                </section>

                <div className="instance-footer">
                    <button className="btn instance-logout-btn" onClick={logout} type="button">
                        Sign Out
                    </button>
                </div>
            </div>

            <style>{`
                .instance-selector {
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--bg-primary);
                    padding: 20px;
                }

                .instance-selector-card {
                    width: 100%;
                    max-width: 480px;
                    background: var(--bg-secondary);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-lg);
                    padding: 36px 32px 28px;
                    box-shadow: var(--shadow-lg);
                    animation: scaleIn 0.25s ease;
                }

                .instance-greeting {
                    text-align: center;
                    color: var(--text-secondary);
                    font-size: 15px;
                    margin-bottom: 28px;
                }

                .instance-greeting strong {
                    color: var(--text-primary);
                }

                .instance-section {
                    margin-bottom: 24px;
                }

                .instance-section-title {
                    font-size: 13px;
                    font-weight: 600;
                    color: var(--text-secondary);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 12px;
                }

                .instance-list {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .instance-item {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 14px;
                    background: var(--bg-tertiary);
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                    transition: border-color var(--transition-fast);
                }

                .instance-item:hover {
                    border-color: var(--accent);
                }

                .instance-item-info {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    min-width: 0;
                }

                .instance-item-name {
                    font-size: 14px;
                    font-weight: 500;
                    color: var(--text-primary);
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                .instance-role {
                    font-size: 11px;
                    font-weight: 500;
                    padding: 2px 8px;
                    border-radius: 999px;
                    background: var(--bg-hover);
                    color: var(--text-secondary);
                    white-space: nowrap;
                }

                .instance-role-owner {
                    background: rgba(108, 140, 255, 0.15);
                    color: var(--accent);
                }

                .instance-role-admin {
                    background: rgba(74, 222, 128, 0.15);
                    color: var(--success);
                }

                .instance-enter-btn {
                    padding: 6px 16px;
                    font-size: 13px;
                    flex-shrink: 0;
                }

                .instance-empty {
                    color: var(--text-muted);
                    font-size: 14px;
                    padding: 12px 0;
                }

                .instance-expand-btn {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    color: var(--text-secondary);
                    border: 1px dashed var(--border);
                    padding: 10px 16px;
                    width: 100%;
                    justify-content: center;
                    font-size: 13px;
                    transition: color var(--transition-fast), border-color var(--transition-fast), background var(--transition-fast);
                }

                .instance-expand-btn:hover {
                    color: var(--accent);
                    border-color: var(--accent);
                    background: var(--accent-dim);
                }

                .instance-create-form {
                    padding: 16px;
                    background: var(--bg-tertiary);
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                }

                .instance-slug-hint {
                    display: block;
                    font-size: 11px;
                    color: var(--text-muted);
                    margin-top: 4px;
                }

                .instance-create-actions {
                    display: flex;
                    gap: 8px;
                    margin-top: 4px;
                }

                .instance-join-btn {
                    color: var(--text-secondary);
                    border: 1px solid var(--border);
                    padding: 10px 16px;
                    width: 100%;
                    font-size: 13px;
                    transition: color var(--transition-fast), border-color var(--transition-fast), background var(--transition-fast);
                }

                .instance-join-btn:hover {
                    color: var(--text-primary);
                    border-color: var(--text-muted);
                    background: var(--bg-tertiary);
                }

                .instance-join-message {
                    margin-top: 12px;
                    padding: 10px 14px;
                    border-radius: var(--radius);
                    font-size: 13px;
                    line-height: 1.4;
                }

                .instance-join-success {
                    background: rgba(74, 222, 128, 0.1);
                    border: 1px solid rgba(74, 222, 128, 0.3);
                    color: var(--success);
                }

                .instance-join-error {
                    background: rgba(248, 113, 113, 0.1);
                    border: 1px solid rgba(248, 113, 113, 0.3);
                    color: var(--error);
                }

                .instance-footer {
                    margin-top: 8px;
                    padding-top: 20px;
                    border-top: 1px solid var(--border);
                    text-align: center;
                }

                .instance-logout-btn {
                    color: var(--text-muted);
                    font-size: 13px;
                    border: none;
                    background: none;
                    padding: 6px 14px;
                }

                .instance-logout-btn:hover {
                    color: var(--text-secondary);
                    background: var(--bg-tertiary);
                }
            `}</style>
        </div>
    );
}
