import { useState, useEffect } from 'react';

export function BillingSection({ currentUser }) {
    const [billing, setBilling] = useState(null);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState(null);
    const [signature, setSignature] = useState('');
    const [signatureSaved, setSignatureSaved] = useState(false);
    const [buyingQueries, setBuyingQueries] = useState(false);

    // BYOK state
    const [llmConfig, setLlmConfig] = useState(null);
    const [models, setModels] = useState(null);
    const [apiKeyInput, setApiKeyInput] = useState('');
    const [savingKey, setSavingKey] = useState(false);
    const [validatingKey, setValidatingKey] = useState(false);
    const [keyStatus, setKeyStatus] = useState(null);
    const [selectedProvider, setSelectedProvider] = useState('');
    const [selectedModel, setSelectedModel] = useState('');
    const [savingConfig, setSavingConfig] = useState(false);

    // SaaS query tier
    const [selectedTier, setSelectedTier] = useState(1);
    const [updatingTier, setUpdatingTier] = useState(false);

    const isOwner = currentUser?.role === 'owner';
    const isByok = billing?.deployment_mode === 'byok';

    const loadBilling = () => {
        setLoading(true);
        fetch('/api/billing/status', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (d) {
                    setBilling(d);
                    setSignature(d.email_signature || '');
                    if (d.query_tier) setSelectedTier(d.query_tier);
                }
                setLoading(false);
            })
            .catch(() => setLoading(false));
    };

    const loadLlmConfig = () => {
        fetch('/api/billing/llm-config', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (d) {
                    setLlmConfig(d);
                    setSelectedProvider(d.provider || 'anthropic');
                    setSelectedModel(d.model || '');
                }
            })
            .catch(() => {});
    };

    const loadModels = () => {
        fetch('/api/billing/available-models', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d) setModels(d); })
            .catch(() => {});
    };

    useEffect(() => {
        loadBilling();
        loadModels();
    }, []);

    useEffect(() => {
        if (billing?.deployment_mode === 'byok') loadLlmConfig();
    }, [billing?.deployment_mode]);

    const handleToggleAddon = async (addon, enable) => {
        setToggling(addon);
        try {
            const res = await fetch('/api/billing/toggle-addon', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ addon, enable }),
                credentials: 'include',
            });
            if (res.ok) loadBilling();
            else {
                const data = await res.json();
                alert(data.detail || 'Failed to toggle addon');
            }
        } catch { alert('Failed to toggle addon'); }
        setToggling(null);
    };

    const handleBuyQueries = async () => {
        setBuyingQueries(true);
        try {
            const res = await fetch('/api/billing/buy-queries', {
                method: 'POST',
                credentials: 'include',
            });
            const data = await res.json();
            if (data.checkout_url) window.location.href = data.checkout_url;
            else alert(data.detail || 'Failed to create checkout session');
        } catch { alert('Failed to create checkout session'); }
        setBuyingQueries(false);
    };

    const handlePortal = async () => {
        try {
            const res = await fetch('/api/billing/portal', {
                method: 'POST',
                credentials: 'include',
            });
            const data = await res.json();
            if (data.portal_url) window.location.href = data.portal_url;
            else alert(data.detail || 'Failed to open billing portal');
        } catch { alert('Failed to open billing portal'); }
    };

    const handleSaveSignature = async () => {
        try {
            const res = await fetch('/api/billing/email-signature', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ signature }),
                credentials: 'include',
            });
            if (res.ok) {
                setSignatureSaved(true);
                setTimeout(() => setSignatureSaved(false), 2000);
            }
        } catch { alert('Failed to save signature'); }
    };

    const handleSetup = async () => {
        try {
            const res = await fetch('/api/billing/setup', {
                method: 'POST',
                credentials: 'include',
            });
            const data = await res.json();
            if (res.ok) loadBilling();
            else alert(data.detail || 'Setup failed');
        } catch { alert('Setup failed'); }
    };

    const handleUpdateTier = async () => {
        setUpdatingTier(true);
        try {
            const res = await fetch('/api/billing/update-query-tier', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tier: selectedTier }),
                credentials: 'include',
            });
            if (res.ok) loadBilling();
            else {
                const data = await res.json();
                alert(data.detail || 'Failed to update tier');
            }
        } catch { alert('Failed to update tier'); }
        setUpdatingTier(false);
    };

    // BYOK handlers
    const handleSaveApiKey = async () => {
        if (!apiKeyInput.trim()) return;
        setSavingKey(true);
        try {
            const res = await fetch('/api/billing/set-api-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKeyInput }),
                credentials: 'include',
            });
            const data = await res.json();
            if (res.ok) {
                setApiKeyInput('');
                setKeyStatus({ valid: true, message: 'Key saved' });
                loadLlmConfig();
            } else {
                setKeyStatus({ valid: false, message: data.detail || 'Failed to save key' });
            }
        } catch { setKeyStatus({ valid: false, message: 'Failed to save key' }); }
        setSavingKey(false);
    };

    const handleValidateKey = async () => {
        setValidatingKey(true);
        setKeyStatus(null);
        try {
            const res = await fetch('/api/billing/validate-key', {
                method: 'POST',
                credentials: 'include',
            });
            const data = await res.json();
            setKeyStatus(data.valid
                ? { valid: true, message: 'Key is valid' }
                : { valid: false, message: data.error || 'Key validation failed' }
            );
            if (data.valid) loadLlmConfig();
        } catch { setKeyStatus({ valid: false, message: 'Validation failed' }); }
        setValidatingKey(false);
    };

    const handleRevokeKey = async () => {
        if (!confirm('Are you sure you want to revoke the API key?')) return;
        try {
            const res = await fetch('/api/billing/api-key', {
                method: 'DELETE',
                credentials: 'include',
            });
            if (res.ok) {
                setKeyStatus(null);
                loadLlmConfig();
            }
        } catch { alert('Failed to revoke key'); }
    };

    const handleSaveLlmConfig = async () => {
        setSavingConfig(true);
        try {
            const res = await fetch('/api/billing/llm-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider: selectedProvider, model: selectedModel || null }),
                credentials: 'include',
            });
            if (res.ok) loadLlmConfig();
            else {
                const data = await res.json();
                alert(data.detail || 'Failed to update config');
            }
        } catch { alert('Failed to update config'); }
        setSavingConfig(false);
    };

    if (loading) return <div className="dashboard-management"><div className="dashboard-management-title">Billing</div><p style={{ color: 'var(--text-secondary)' }}>Loading...</p></div>;
    if (!billing) return null;

    const providerModels = models?.[selectedProvider] || [];
    const qualityColors = { 'Excellent': '#4ade80', 'Very Good': '#86efac', 'Good': '#fbbf24', 'Moderate': '#f97316' };

    const handleSwitchMode = async (mode) => {
        const label = mode === 'byok' ? 'Bring Your Own Key' : 'SaaS (managed)';
        if (!confirm(`Switch to ${label} mode? ${mode === 'byok' ? 'You will need to provide your own LLM API key.' : 'Your queries will be managed by TrueCore.cloud.'}`)) return;
        try {
            const res = await fetch('/api/billing/deployment-mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode }),
                credentials: 'include',
            });
            if (res.ok) {
                loadBilling();
                if (mode === 'byok') loadLlmConfig();
            } else {
                const data = await res.json();
                alert(data.detail || 'Failed to switch mode');
            }
        } catch { alert('Failed to switch mode'); }
    };

    return (
        <div className="dashboard-management">
            <div className="dashboard-management-title">Billing & Subscription</div>

            {/* Deployment mode selector */}
            {isOwner && (
                <div style={{ marginBottom: 16, padding: 12, background: 'var(--surface-secondary)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Mode:</span>
                    <button
                        className={`btn btn-sm ${!isByok ? 'btn-primary' : ''}`}
                        onClick={() => !isByok || handleSwitchMode('saas')}
                        style={!isByok ? {} : { opacity: 0.7 }}
                    >
                        SaaS ({'\u20AC'}24.99/250 queries)
                    </button>
                    <button
                        className={`btn btn-sm ${isByok ? 'btn-primary' : ''}`}
                        onClick={() => isByok || handleSwitchMode('byok')}
                        style={isByok ? {} : { opacity: 0.7 }}
                    >
                        Bring Your Own Key ({'\u20AC'}9.99/user)
                    </button>
                </div>
            )}

            {/* SaaS: Query Tier Selector */}
            {!isByok && isOwner && billing.tier === 'paid' && (
                <div className="billing-tier-section" style={{ marginBottom: 16, padding: 12, background: 'var(--surface-secondary)', borderRadius: 8 }}>
                    <div className="billing-label" style={{ marginBottom: 8 }}>Query Plan</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <select
                            value={selectedTier}
                            onChange={e => setSelectedTier(Number(e.target.value))}
                            className="form-input"
                            style={{ width: 240 }}
                        >
                            {Array.from({ length: 40 }, (_, i) => i + 1).map(t => (
                                <option key={t} value={t}>{t * 250} queries/mo - {'\u20AC'}{(t * 24.99).toFixed(2)}/mo</option>
                            ))}
                        </select>
                        {selectedTier !== billing.query_tier && (
                            <button className="btn btn-sm btn-primary" onClick={handleUpdateTier} disabled={updatingTier}>
                                {updatingTier ? 'Updating...' : 'Update Plan'}
                            </button>
                        )}
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 6 }}>
                        Need more than 10,000 queries/month? <a href="mailto:gocandan@gmail.com" style={{ color: 'var(--accent)' }}>Contact us</a>
                    </p>
                </div>
            )}

            {isOwner && (
                <div className="billing-actions">
                    {!isByok && (
                        <button className="btn btn-sm btn-primary" onClick={handleBuyQueries} disabled={buyingQueries}>
                            {buyingQueries ? 'Redirecting...' : 'Buy 250 Queries (\u20AC19.99)'}
                        </button>
                    )}
                    {billing.has_subscription && (
                        <button className="btn btn-sm" onClick={handlePortal}>Manage Payment Method</button>
                    )}
                    {!billing.has_subscription && (
                        <button className="btn btn-sm btn-primary" onClick={handleSetup}>Set Up Billing</button>
                    )}
                </div>
            )}

            {/* BYOK: LLM Configuration */}
            {isByok && isOwner && (
                <div style={{ marginBottom: 16, padding: 16, background: 'var(--surface-secondary)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
                    <div className="billing-label" style={{ marginBottom: 12, fontSize: 14 }}>LLM Configuration</div>

                    <div style={{ fontSize: 12, color: '#f59e0b', marginBottom: 14, padding: 10, background: 'rgba(245, 158, 11, 0.08)', borderRadius: 6, border: '1px solid rgba(245, 158, 11, 0.2)', lineHeight: 1.5 }}>
                        TrueCore.cloud is built and optimised for Anthropic's Claude models, including Anthropic's prompt caching to reduce costs and improve response quality. While we support other providers, using a non-Anthropic key may result in higher costs (no caching), degraded tool execution, or unexpected behaviour. We cannot take responsibility for performance issues when using third-party providers.
                    </div>

                    {/* Provider & Model Selection */}
                    <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                        <div style={{ flex: 1 }}>
                            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Provider</label>
                            <select
                                value={selectedProvider}
                                onChange={e => {
                                    setSelectedProvider(e.target.value);
                                    const firstModel = models?.[e.target.value]?.[0];
                                    setSelectedModel(firstModel?.id || '');
                                }}
                                className="form-input"
                                style={{ width: '100%' }}
                            >
                                <option value="anthropic">Anthropic</option>
                                <option value="openai">OpenAI</option>
                                <option value="google">Google</option>
                                <option value="deepseek">DeepSeek</option>
                            </select>
                        </div>
                        <div style={{ flex: 1 }}>
                            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Model</label>
                            <select
                                value={selectedModel}
                                onChange={e => setSelectedModel(e.target.value)}
                                className="form-input"
                                style={{ width: '100%' }}
                            >
                                {providerModels.map(m => (
                                    <option key={m.id} value={m.id}>
                                        {m.name} ({m.tool_quality})
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Model quality indicator */}
                    {selectedModel && providerModels.length > 0 && (() => {
                        const model = providerModels.find(m => m.id === selectedModel);
                        if (!model) return null;
                        const color = qualityColors[model.tool_quality] || '#94a3b8';
                        return (
                            <div style={{ fontSize: 12, marginBottom: 12 }}>
                                <span style={{ color }}>Tool quality: {model.tool_quality}</span>
                                {model.tool_quality === 'Moderate' && (
                                    <span style={{ color: '#f97316', marginLeft: 8 }}>May struggle with complex multi-step operations</span>
                                )}
                            </div>
                        );
                    })()}

                    {/* Prompt caching info */}
                    {selectedProvider !== 'anthropic' && (
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 12, padding: 8, background: 'var(--surface-primary)', borderRadius: 4 }}>
                            Anthropic models benefit from prompt caching, which can reduce your per-conversation costs by ~60%. Other providers do not support this feature.
                        </div>
                    )}

                    {(selectedProvider !== llmConfig?.provider || selectedModel !== llmConfig?.model) && (
                        <button className="btn btn-sm btn-primary" onClick={handleSaveLlmConfig} disabled={savingConfig} style={{ marginBottom: 12 }}>
                            {savingConfig ? 'Saving...' : 'Save Provider & Model'}
                        </button>
                    )}

                    {/* API Key Management */}
                    <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
                        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>API Key</label>
                        {llmConfig?.has_api_key ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span className="form-input" style={{ flex: 1, background: 'var(--surface-primary)', cursor: 'default' }}>
                                    {llmConfig.masked_key || '****'}
                                </span>
                                <button className="btn btn-sm" onClick={handleValidateKey} disabled={validatingKey}>
                                    {validatingKey ? 'Testing...' : 'Test'}
                                </button>
                                <button className="btn btn-sm" onClick={handleRevokeKey} style={{ color: '#ef4444' }}>Revoke</button>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', gap: 8 }}>
                                <input
                                    type="password"
                                    value={apiKeyInput}
                                    onChange={e => setApiKeyInput(e.target.value)}
                                    placeholder="Paste your API key..."
                                    className="form-input"
                                    style={{ flex: 1 }}
                                />
                                <button className="btn btn-sm btn-primary" onClick={handleSaveApiKey} disabled={savingKey || !apiKeyInput.trim()}>
                                    {savingKey ? 'Saving...' : 'Save Key'}
                                </button>
                            </div>
                        )}
                        {keyStatus && (
                            <div style={{ fontSize: 12, marginTop: 4, color: keyStatus.valid ? '#4ade80' : '#ef4444' }}>
                                {keyStatus.valid ? '\u2713' : '\u2717'} {keyStatus.message}
                            </div>
                        )}
                        {llmConfig?.llm_key_last_validated && (
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                                Last validated: {new Date(llmConfig.llm_key_last_validated).toLocaleString()}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* BYOK read-only config for non-owners */}
            {isByok && !isOwner && llmConfig && (
                <div style={{ marginBottom: 16, padding: 12, background: 'var(--surface-secondary)', borderRadius: 8, fontSize: 13 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>LLM Provider: </span>
                    <span>{llmConfig.provider}</span>
                    {llmConfig.model && <>
                        <span style={{ color: 'var(--text-secondary)', marginLeft: 12 }}>Model: </span>
                        <span>{llmConfig.model}</span>
                    </>}
                </div>
            )}

            {/* Addons */}
            {isOwner && (
                <div className="billing-addons">
                    <div className="billing-addon">
                        <div className="billing-addon-header">
                            <div className="billing-addon-info">
                                <span className="billing-addon-name">Email Addon</span>
                                <span className="billing-addon-price">$4.99/mo</span>
                            </div>
                            <label className="billing-toggle">
                                <input type="checkbox" checked={billing.email_addon} disabled={toggling === 'email'} onChange={e => handleToggleAddon('email', e.target.checked)} />
                                <span className="billing-toggle-slider" />
                            </label>
                        </div>
                        <p className="billing-addon-desc">Send emails directly from TrueCore.cloud through natural language. Includes up to 100 emails per month.</p>
                    </div>

                    <div className="billing-addon">
                        <div className="billing-addon-header">
                            <div className="billing-addon-info">
                                <span className="billing-addon-name">Daily Reports Addon</span>
                                <span className="billing-addon-price">$4.99/mo</span>
                            </div>
                            <label className="billing-toggle">
                                <input type="checkbox" checked={billing.daily_reports_addon} disabled={toggling === 'daily_reports'} onChange={e => handleToggleAddon('daily_reports', e.target.checked)} />
                                <span className="billing-toggle-slider" />
                            </label>
                        </div>
                        <p className="billing-addon-desc">Receive automated daily operations reports every morning to all site supervisors.</p>
                    </div>

                    <div className="billing-addon">
                        <div className="billing-addon-header">
                            <div className="billing-addon-info">
                                <span className="billing-addon-name">Receive Tickets on Email</span>
                                <span className="billing-addon-price">$24.99/mo</span>
                            </div>
                            <label className="billing-toggle">
                                <input type="checkbox" checked={billing.inbound_email_addon} disabled={toggling === 'inbound_email'} onChange={e => handleToggleAddon('inbound_email', e.target.checked)} />
                                <span className="billing-toggle-slider" />
                            </label>
                        </div>
                        <p className="billing-addon-desc">External users can email to automatically create tickets. AI extracts fields and sends confirmation.</p>
                    </div>

                    <div className="billing-addon">
                        <div className="billing-addon-header">
                            <div className="billing-addon-info">
                                <span className="billing-addon-name">Bookings Addon</span>
                                <span className="billing-addon-price">$4.99/mo</span>
                            </div>
                            <label className="billing-toggle">
                                <input type="checkbox" checked={billing.bookings_addon} disabled={toggling === 'bookings'} onChange={e => handleToggleAddon('bookings', e.target.checked)} />
                                <span className="billing-toggle-slider" />
                            </label>
                        </div>
                        <p className="billing-addon-desc">Book rooms, desks, parking spaces, and assets through chat or email.</p>
                    </div>

                    <div className="billing-enterprise">
                        <div className="billing-addon-info">
                            <span className="billing-addon-name">Enterprise</span>
                        </div>
                        <ul className="billing-enterprise-benefits">
                            <li>Custom database</li>
                            <li>Separation of database on own instance</li>
                        </ul>
                        <a href="mailto:gocandan@gmail.com" className="btn btn-primary btn-sm">Contact Us</a>
                    </div>
                </div>
            )}

            {/* Email signature */}
            {billing.email_addon && (
                <div className="billing-signature">
                    <div className="billing-label">Email Signature</div>
                    <textarea
                        className="form-input billing-signature-input"
                        value={signature}
                        onChange={e => setSignature(e.target.value)}
                        placeholder="Appended to all outgoing emails..."
                        rows={3}
                    />
                    <button className="btn btn-sm" onClick={handleSaveSignature}>
                        {signatureSaved ? 'Saved' : 'Save Signature'}
                    </button>
                </div>
            )}

            {/* Event history */}
            {billing.events && billing.events.length > 0 && (
                <div className="billing-events">
                    <div className="billing-label" style={{ marginBottom: 8 }}>Recent Activity</div>
                    {billing.events.slice(0, 10).map((evt, i) => (
                        <div key={i} className="billing-event-row">
                            <span className="billing-event-type">{evt.event_type.replace(/_/g, ' ')}</span>
                            {evt.details && <span className="billing-event-detail">{evt.details}</span>}
                            <span className="billing-event-date">{new Date(evt.created_at).toLocaleDateString()}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
