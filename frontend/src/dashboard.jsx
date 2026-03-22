import { useState, useEffect, useRef } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell,
    ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { BillingSection } from './billing';

const COLORS = ['#6c8cff', '#4ade80', '#f87171', '#fbbf24', '#a78bfa', '#38bdf8'];
const AVATAR_COLORS = ['#6c8cff', '#4ade80', '#f87171', '#fbbf24', '#a78bfa', '#38bdf8', '#f472b6', '#34d399', '#fb923c', '#818cf8'];

const tooltipStyle = {
    contentStyle: { background: '#1a1d27', border: '1px solid #2d3045', borderRadius: 8, fontSize: 13 },
    labelStyle: { color: '#9ca0b0' },
};

const CARD_ACCENTS = {
    'Active Assets': '#6c8cff',
    'Open Tickets': '#4ade80',
    'Open Issues': '#f87171',
    'Events This Week': '#fbbf24',
    'Flagged Important': '#a78bfa',
};

function StatCard({ label, value, accent }) {
    return (
        <div className="dashboard-card" style={{ borderTop: `3px solid ${accent || 'var(--accent)'}` }}>
            <div className="dashboard-card-value">{value ?? '\u2014'}</div>
            <div className="dashboard-card-label">{label}</div>
        </div>
    );
}

function ChartBox({ title, children }) {
    return (
        <div className="dashboard-chart">
            <h4>{title}</h4>
            {children}
        </div>
    );
}

function EmptyChart() {
    return (
        <div className="empty-chart">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
                <line x1="2" y1="20" x2="22" y2="20"/>
            </svg>
            <span>No data yet</span>
        </div>
    );
}

function RemindersSection() {
    const [reminders, setReminders] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadReminders = () => {
        fetch('/api/reminders', { credentials: 'include' })
            .then(r => r.json())
            .then(d => { setReminders(d.reminders || []); setLoading(false); })
            .catch(() => setLoading(false));
    };

    useEffect(() => { loadReminders(); }, []);

    const cancelReminder = async (id) => {
        const res = await fetch(`/api/reminders/${id}`, { method: 'DELETE', credentials: 'include' });
        const data = await res.json();
        if (data.ok) loadReminders();
        else alert(data.error || 'Failed to cancel reminder');
    };

    const formatDate = (iso) => {
        if (!iso) return '';
        const d = new Date(iso);
        return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    const recurrenceLabel = (r) => {
        if (r === 'one_time') return 'Once';
        return r.charAt(0).toUpperCase() + r.slice(1);
    };

    if (loading) return null;

    return (
        <div className="dashboard-management">
            <div className="dashboard-management-title">Reminders</div>
            {reminders.length === 0 ? (
                <div className="dashboard-management-hint">
                    No active reminders. Use the chat to create one — try "remind me to check the server room tomorrow at 9am".
                </div>
            ) : (
                <div className="reminders-list">
                    {reminders.map(r => (
                        <div key={r.id} className="reminder-row">
                            <div className="reminder-info">
                                <span className="reminder-title">{r.title}</span>
                                <span className="reminder-meta">
                                    {formatDate(r.remind_at)} &middot; {recurrenceLabel(r.recurrence)}
                                    {r.notify_person_name && <> &middot; {r.notify_person_name}</>}
                                </span>
                            </div>
                            <button className="btn btn-sm btn-danger" onClick={() => cancelReminder(r.id)}>Cancel</button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function QueryPoolSection() {
    const [usage, setUsage] = useState(null);
    useEffect(() => {
        fetch('/api/dashboard/usage', { credentials: 'include' })
            .then(r => r.json()).then(setUsage).catch(console.error);
    }, []);
    if (!usage) return null;
    const remaining = usage.queries_remaining;
    const total = usage.query_limit;
    const usedPct = total > 0 ? Math.min(100, ((total - remaining) / total) * 100) : 0;
    const resetDate = usage.query_pool_reset_at ? new Date(usage.query_pool_reset_at).toLocaleDateString() : null;
    const isFree = usage.tier === 'free';

    return (
        <div className="dashboard-management">
            <div className="dashboard-management-title">Query Pool</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span className="query-pool-remaining">{remaining}</span>
                <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>of {total} queries remaining</span>
            </div>
            <div className="billing-usage-bar" style={{ marginTop: 8 }}>
                <div className="billing-usage-fill" style={{ width: `${usedPct}%`, background: usedPct > 80 ? '#f87171' : usedPct > 60 ? '#fbbf24' : '#4ade80' }} />
            </div>
            <div className="query-pool-explanation">
                A query is one interaction with the AI assistant in Chat.
                {isFree && <><br />Your instance received 60 free queries for demo purposes.</>}
                <br />Each added user contributes 250 queries/month to the pool. {usage.seat_count} user{usage.seat_count !== 1 ? 's' : ''} x 250 = {usage.base_queries} base queries.
                {resetDate && <><br />Pool resets on {resetDate}.</>}
            </div>
        </div>
    );
}

function UserCard({ user, currentUser, onRoleChange, onRemove, onMottoSaved }) {
    const [editingMotto, setEditingMotto] = useState(false);
    const [mottoVal, setMottoVal] = useState(user.motto || '');
    const isOwnCard = currentUser?.person_id === user.id;
    const initials = (user.first_name?.[0] || '') + (user.last_name?.[0] || '');
    const color = AVATAR_COLORS[user.id % AVATAR_COLORS.length];

    const saveMotto = async () => {
        const res = await fetch(`/api/dashboard/users/${user.id}/motto`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ motto: mottoVal, requesting_person_id: currentUser?.person_id }),
        });
        const data = await res.json();
        if (data.ok) { setEditingMotto(false); onMottoSaved(); }
        else alert(data.error || 'Failed to save motto');
    };

    return (
        <div className="user-card">
            <div className="user-card-avatar" style={{ background: color }}>{initials.toUpperCase()}</div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>{user.first_name} {user.last_name}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{user.email || 'No email'}</div>
            <span className={`user-role-badge role-${user.user_role}`}>{user.user_role}</span>
            {editingMotto ? (
                <div style={{ width: '100%', display: 'flex', gap: 4 }}>
                    <input
                        className="form-input"
                        style={{ flex: 1, fontSize: 12 }}
                        value={mottoVal}
                        onChange={e => setMottoVal(e.target.value)}
                        maxLength={200}
                        placeholder="Your motto..."
                        onKeyDown={e => e.key === 'Enter' && saveMotto()}
                    />
                    <button className="btn btn-sm btn-primary" onClick={saveMotto}>Save</button>
                    <button className="btn btn-sm" onClick={() => { setEditingMotto(false); setMottoVal(user.motto || ''); }}>Cancel</button>
                </div>
            ) : (
                <div className="user-card-motto" onClick={isOwnCard ? () => setEditingMotto(true) : undefined} style={isOwnCard ? { cursor: 'pointer' } : {}}>
                    {user.motto || (isOwnCard ? 'Click to add a motto...' : '')}
                </div>
            )}
            {(currentUser?.role === 'owner' || currentUser?.role === 'admin') && user.user_role !== 'owner' && (
                <div className="user-actions" style={{ marginTop: 4 }}>
                    {currentUser?.role === 'owner' && (
                        <select className="btn btn-sm" value={user.user_role} onChange={e => onRoleChange(user.id, e.target.value)}>
                            <option value="user">user</option>
                            <option value="admin">admin</option>
                        </select>
                    )}
                    {(currentUser?.role === 'owner' || (currentUser?.role === 'admin' && user.user_role === 'user')) && (
                        <button className="btn btn-sm btn-danger" onClick={() => onRemove(user.id)}>Remove</button>
                    )}
                </div>
            )}
        </div>
    );
}

export function DashboardPage({ currentUser }) {
    const [overview, setOverview] = useState(null);
    const [assets, setAssets] = useState([]);
    const [issues, setIssues] = useState({ by_status: [], by_severity: [] });
    const [staff, setStaff] = useState([]);
    const [refreshedAt, setRefreshedAt] = useState(null);
    const [reportStatus, setReportStatus] = useState(null);
    const [importing, setImporting] = useState(false);
    const importRef = useRef(null);
    const [users, setUsers] = useState([]);
    const [addingUser, setAddingUser] = useState(false);
    const [newUser, setNewUser] = useState({ first_name: '', last_name: '', email: '', role: 'user' });

    const isPrivileged = ['admin', 'owner'].includes(currentUser?.role);

    const loadUsers = () => {
        fetch('/api/dashboard/users').then(r => r.json()).then(d => setUsers(d.users || [])).catch(console.error);
    };

    const handleAddUser = async () => {
        const res = await fetch('/api/dashboard/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...newUser, requesting_person_id: currentUser?.person_id }),
        });
        const data = await res.json();
        if (data.ok) {
            setAddingUser(false);
            setNewUser({ first_name: '', last_name: '', email: '', role: 'user' });
            loadUsers();
            loadUsers();
        } else {
            alert(data.error || 'Failed to add user');
        }
    };

    const handleRemoveUser = async (personId) => {
        if (!window.confirm('Remove this user?')) return;
        const res = await fetch(`/api/dashboard/users/${personId}?requesting_person_id=${currentUser?.person_id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) { loadUsers(); loadUsers(); }
        else alert(data.error || 'Failed to remove user');
    };

    const handleRoleChange = async (personId, newRole) => {
        const res = await fetch(`/api/dashboard/users/${personId}/role`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_role: newRole, requesting_person_id: currentUser?.person_id }),
        });
        const data = await res.json();
        if (data.ok) { loadUsers(); loadUsers(); }
        else alert(data.error || 'Failed to change role');
    };

    const sendDailyReport = async () => {
        setReportStatus('sending');
        try {
            const res = await fetch('/api/admin/send-daily-report', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                setReportStatus(`Sent to ${data.details?.length ?? 0}`);
            } else {
                setReportStatus('Error');
            }
        } catch {
            setReportStatus('Error');
        }
        setTimeout(() => setReportStatus(null), 3000);
    };

    function loadDashboard() {
        Promise.all([
            fetch('/api/dashboard/overview').then(r => r.json()),
            fetch('/api/dashboard/assets-by-period').then(r => r.json()),
            fetch('/api/dashboard/issues-summary').then(r => r.json()),
            fetch('/api/dashboard/staff-per-site').then(r => r.json()),
        ]).then(([ov, as, is_, st]) => {
            setOverview(ov);
            setAssets(as.data || []);
            setIssues(is_);
            setStaff(st.data || []);
            setRefreshedAt(new Date());
        }).catch(console.error);
    }

    useEffect(() => { loadDashboard(); loadUsers(); }, []);

    const handleImportMerge = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        e.target.value = '';
        setImporting(true);
        try {
            const form = new FormData();
            form.append('file', file);
            const res = await fetch('/api/tables/import-merge', { method: 'POST', body: form });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            const msg = `Merged ${data.tables_imported} table(s).\n` +
                Object.entries(data.rows_per_table).map(([t, n]) => `  ${t}: ${n} new rows`).join('\n') +
                (data.skipped_sheets.length ? `\nSkipped: ${data.skipped_sheets.join(', ')}` : '') +
                (data.errors.length ? `\nErrors:\n  ${data.errors.join('\n  ')}` : '');
            alert(msg);
            loadDashboard();
        } catch (err) { alert('Import failed: ' + err.message); }
        setImporting(false);
    };

    function handleResetDatabase() {
        if (!window.confirm('This will permanently delete ALL data and recreate empty tables. Continue?')) return;
        fetch('/api/dashboard/reset-database', { method: 'POST' })
            .then(r => r.json())
            .then(res => {
                if (res.ok) loadDashboard();
                else alert('Reset failed: ' + (res.error || 'Unknown error'));
            })
            .catch(err => alert('Reset failed: ' + err.message));
    }

    const refreshedLabel = refreshedAt
        ? `Last refreshed: ${refreshedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
        : '';

    return (
        <div className="dashboard-container">
            <div className="dashboard-header">
                <h2 className="dashboard-title">Dashboard</h2>
                {refreshedLabel && <span className="dashboard-refreshed">{refreshedLabel}</span>}
            </div>

            <div className="dashboard-cards">
                <StatCard label="Active Assets" value={overview?.active_assets} accent={CARD_ACCENTS['Active Assets']} />
                <StatCard label="Open Tickets" value={overview?.open_tickets} accent={CARD_ACCENTS['Open Tickets']} />
                <StatCard label="Open Issues" value={overview?.open_issues} accent={CARD_ACCENTS['Open Issues']} />
                <StatCard label="Events This Week" value={overview?.events_this_week} accent={CARD_ACCENTS['Events This Week']} />
                <StatCard label="Flagged Important" value={overview?.important_items} accent={CARD_ACCENTS['Flagged Important']} />
            </div>

            <div className="dashboard-grid">
                <ChartBox title="Assets Added Over Time">
                    {assets.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={assets}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3045" />
                                <XAxis dataKey="date" tick={{ fill: '#9ca0b0', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#9ca0b0', fontSize: 11 }} allowDecimals={false} />
                                <Tooltip {...tooltipStyle} cursor={false} />
                                <Bar dataKey="count" fill="#6c8cff" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : <EmptyChart />}
                </ChartBox>

                <ChartBox title="Issues by Severity">
                    {issues.by_severity.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <PieChart>
                                <Pie
                                    data={issues.by_severity}
                                    dataKey="count"
                                    nameKey="severity"
                                    cx="50%" cy="50%"
                                    outerRadius={90}
                                    label={({ severity, count }) => `${severity}: ${count}`}
                                    labelLine={false}
                                >
                                    {issues.by_severity.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip {...tooltipStyle} cursor={false} />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : <EmptyChart />}
                </ChartBox>

                <ChartBox title="Tickets by Status">
                    {issues.by_status.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={issues.by_status} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3045" />
                                <XAxis type="number" tick={{ fill: '#9ca0b0', fontSize: 11 }} allowDecimals={false} />
                                <YAxis type="category" dataKey="status" tick={{ fill: '#9ca0b0', fontSize: 11 }} width={100} />
                                <Tooltip {...tooltipStyle} cursor={false} />
                                <Bar dataKey="count" fill="#4ade80" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : <EmptyChart />}
                </ChartBox>

                <ChartBox title="Staff per Site">
                    {staff.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={staff}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3045" />
                                <XAxis dataKey="site" tick={{ fill: '#9ca0b0', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#9ca0b0', fontSize: 11 }} allowDecimals={false} />
                                <Tooltip {...tooltipStyle} cursor={false} />
                                <Bar dataKey="count" fill="#a78bfa" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : <EmptyChart />}
                </ChartBox>
            </div>

            {overview?.last_push && (
                <p className="dashboard-footer-text">
                    Version pushed to GitHub at: {new Date(overview.last_push).toLocaleString()}
                </p>
            )}

            <QueryPoolSection />

            <RemindersSection />

            {currentUser?.role === 'owner' && (
                <BillingSection currentUser={currentUser} />
            )}

            <div className="dashboard-management">
                <div className="dashboard-management-title">User Management</div>
                <div className="user-cards-grid">
                    {users.map(u => (
                        <UserCard
                            key={u.id}
                            user={u}
                            currentUser={currentUser}
                            onRoleChange={handleRoleChange}
                            onRemove={handleRemoveUser}
                            onMottoSaved={loadUsers}
                        />
                    ))}
                </div>
                {isPrivileged && (
                    addingUser ? (
                        <div className="add-user-form">
                            <input className="form-input" placeholder="First name" value={newUser.first_name} onChange={e => setNewUser({ ...newUser, first_name: e.target.value })} />
                            <input className="form-input" placeholder="Last name" value={newUser.last_name} onChange={e => setNewUser({ ...newUser, last_name: e.target.value })} />
                            <input className="form-input" placeholder="Email" type="email" value={newUser.email} onChange={e => setNewUser({ ...newUser, email: e.target.value })} />
                            {currentUser?.role === 'owner' && (
                                <select className="form-input" value={newUser.role} onChange={e => setNewUser({ ...newUser, role: e.target.value })}>
                                    <option value="user">user</option>
                                    <option value="admin">admin</option>
                                </select>
                            )}
                            <div className="add-user-actions">
                                <button className="btn btn-sm btn-primary" onClick={handleAddUser}>Add &amp; Send Invite</button>
                                <button className="btn btn-sm" onClick={() => setAddingUser(false)}>Cancel</button>
                            </div>
                        </div>
                    ) : (
                        <div className="dashboard-management-row" style={{ marginTop: 12 }}>
                            <button className="btn btn-sm btn-primary" onClick={() => setAddingUser(true)}>+ Add User</button>
                        </div>
                    )
                )}
            </div>

            <div className="dashboard-management">
                <div className="dashboard-management-title">Database Management</div>
                <div className="dashboard-management-row">
                    <a href="/api/tables/export" download className="btn btn-sm">Export .xlsx</a>
                    <button
                        className="btn btn-sm btn-primary"
                        disabled={importing}
                        onClick={() => importRef.current?.click()}
                    >
                        {importing ? 'Importing...' : 'Import & Merge'}
                    </button>
                    <input
                        type="file"
                        accept=".xlsx"
                        ref={importRef}
                        style={{ display: 'none' }}
                        onChange={handleImportMerge}
                    />
                </div>
                <div className="dashboard-management-hint">
                    Import merges new rows into existing tables. Duplicates are skipped.
                </div>
            </div>

            <div className="dashboard-management">
                <div className="dashboard-management-title">Admin Actions</div>
                <div className="dashboard-management-row">
                    {isPrivileged && (
                        <button
                            className="btn btn-sm"
                            onClick={sendDailyReport}
                            disabled={reportStatus === 'sending'}
                        >
                            {reportStatus === 'sending' ? 'Sending...' : reportStatus ?? 'Send Daily Report'}
                        </button>
                    )}
                    <button className="btn btn-sm btn-danger" onClick={handleResetDatabase}>
                        Reset Database
                    </button>
                </div>
            </div>
        </div>
    );
}
