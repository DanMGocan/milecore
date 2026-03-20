import { useState, useEffect } from 'react';

export function BillingSection({ currentUser }) {
    const [billing, setBilling] = useState(null);
    const [loading, setLoading] = useState(true);
    const [toggling, setToggling] = useState(null);
    const [signature, setSignature] = useState('');
    const [signatureSaved, setSignatureSaved] = useState(false);
    const [buyingQueries, setBuyingQueries] = useState(false);

    const isOwner = currentUser?.role === 'owner';

    const loadBilling = () => {
        setLoading(true);
        fetch('/api/billing/status', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (d) {
                    setBilling(d);
                    setSignature(d.email_signature || '');
                }
                setLoading(false);
            })
            .catch(() => setLoading(false));
    };

    useEffect(() => { loadBilling(); }, []);

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
            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            } else {
                alert(data.detail || 'Failed to create checkout session');
            }
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
            if (data.portal_url) {
                window.location.href = data.portal_url;
            } else {
                alert(data.detail || 'Failed to open billing portal');
            }
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

    if (loading) return <div className="dashboard-management"><div className="dashboard-management-title">Billing</div><p style={{ color: 'var(--text-secondary)' }}>Loading...</p></div>;
    if (!billing) return null;

    const usagePct = billing.query_limit > 0 ? Math.min(100, (billing.query_count / billing.query_limit) * 100) : 0;
    const resetDate = billing.query_pool_reset_at ? new Date(billing.query_pool_reset_at).toLocaleDateString() : null;

    return (
        <div className="dashboard-management">
            <div className="dashboard-management-title">Billing & Subscription</div>

            {/* Plan summary */}
            <div className="billing-summary">
                <div className="billing-row">
                    <span className="billing-label">Plan</span>
                    <span className="billing-value">{billing.tier === 'paid' ? 'Pro' : 'Free'} - {billing.seat_count} seat{billing.seat_count !== 1 ? 's' : ''} @ $24.99/seat/mo</span>
                </div>
                {billing.subscription_status && (
                    <div className="billing-row">
                        <span className="billing-label">Status</span>
                        <span className={`billing-status billing-status-${billing.subscription_status}`}>{billing.subscription_status}</span>
                    </div>
                )}
            </div>

            {/* Query usage */}
            <div className="billing-usage">
                <div className="billing-row">
                    <span className="billing-label">Query Pool</span>
                    <span className="billing-value">{billing.query_count} / {billing.query_limit} used</span>
                </div>
                <div className="billing-usage-bar">
                    <div className="billing-usage-fill" style={{ width: `${usagePct}%`, background: usagePct > 80 ? '#f87171' : usagePct > 60 ? '#fbbf24' : '#4ade80' }} />
                </div>
                <div className="billing-pool-breakdown">
                    {billing.seat_count} user{billing.seat_count !== 1 ? 's' : ''} x 250 = {billing.base_queries} base
                    {billing.purchased_queries > 0 && ` + ${billing.purchased_queries} purchased`}
                    {' '}= {billing.query_limit} total
                </div>
                {resetDate && <div className="billing-reset-date">Resets on {resetDate}</div>}
            </div>

            {isOwner && (
                <div className="billing-actions">
                    <button className="btn btn-sm btn-primary" onClick={handleBuyQueries} disabled={buyingQueries}>
                        {buyingQueries ? 'Redirecting...' : 'Buy 250 Queries ($19.99)'}
                    </button>
                    {billing.has_subscription && (
                        <button className="btn btn-sm" onClick={handlePortal}>Manage Payment Method</button>
                    )}
                    {!billing.has_subscription && (
                        <button className="btn btn-sm btn-primary" onClick={handleSetup}>Set Up Billing</button>
                    )}
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
                                <input
                                    type="checkbox"
                                    checked={billing.email_addon}
                                    disabled={toggling === 'email'}
                                    onChange={e => handleToggleAddon('email', e.target.checked)}
                                />
                                <span className="billing-toggle-slider" />
                            </label>
                        </div>
                        <p className="billing-addon-desc">
                            Send emails directly from TrueCore.cloud through natural language. Just tell the AI who to email and what to say.
                            Includes up to 100 emails per month.
                        </p>
                    </div>

                    <div className="billing-addon">
                        <div className="billing-addon-header">
                            <div className="billing-addon-info">
                                <span className="billing-addon-name">Daily Reports Addon</span>
                                <span className="billing-addon-price">$4.99/mo</span>
                            </div>
                            <label className="billing-toggle">
                                <input
                                    type="checkbox"
                                    checked={billing.daily_reports_addon}
                                    disabled={toggling === 'daily_reports'}
                                    onChange={e => handleToggleAddon('daily_reports', e.target.checked)}
                                />
                                <span className="billing-toggle-slider" />
                            </label>
                        </div>
                        <p className="billing-addon-desc">
                            Receive automated daily operations reports every morning. TrueCore.cloud compiles new issues, scheduled vendor visits,
                            and items flagged as important — then emails a summary to all site supervisors.
                        </p>
                    </div>

                    <div className="billing-addon">
                        <div className="billing-addon-header">
                            <div className="billing-addon-info">
                                <span className="billing-addon-name">Receive Tickets on Email</span>
                                <span className="billing-addon-price">$24.99/mo</span>
                            </div>
                            <label className="billing-toggle">
                                <input
                                    type="checkbox"
                                    checked={billing.inbound_email_addon}
                                    disabled={toggling === 'inbound_email'}
                                    onChange={e => handleToggleAddon('inbound_email', e.target.checked)}
                                />
                                <span className="billing-toggle-slider" />
                            </label>
                        </div>
                        <p className="billing-addon-desc">
                            External users can email {billing.slug}@tickets.truecore.cloud to automatically create tickets.
                            AI extracts all relevant fields, creates the ticket, and sends a confirmation back to the sender.
                            Control who can submit tickets via the sender whitelist.
                        </p>
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
