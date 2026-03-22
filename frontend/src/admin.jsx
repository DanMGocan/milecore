import { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
    ResponsiveContainer, CartesianGrid,
} from 'recharts';

const ADMIN_EMAIL = 'gocandan@gmail.com';

const tooltipStyle = {
    contentStyle: { background: '#1a1d27', border: '1px solid #2d3045', borderRadius: 8, fontSize: 13 },
    labelStyle: { color: '#9ca0b0' },
};

function StatCard({ label, value, accent }) {
    return (
        <div className="dashboard-card" style={{ borderTop: `3px solid ${accent || 'var(--accent)'}` }}>
            <div className="dashboard-card-value">{value ?? '\u2014'}</div>
            <div className="dashboard-card-label">{label}</div>
        </div>
    );
}

function formatNum(n) {
    if (n == null) return '\u2014';
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
    return String(n);
}

export function AdminPage() {
    const { user } = useAuth();
    const [stats, setStats] = useState(null);
    const [users, setUsers] = useState([]);
    const [instances, setInstances] = useState([]);
    const [payments, setPayments] = useState({ purchases: [], subscription_events: [] });
    const [tokenData, setTokenData] = useState([]);
    const [activeTab, setActiveTab] = useState('users');
    const [loading, setLoading] = useState(true);
    const [sortCol, setSortCol] = useState(null);
    const [sortDir, setSortDir] = useState('asc');

    if (user?.email !== ADMIN_EMAIL) {
        return (
            <div className="dashboard-container" style={{ textAlign: 'center', paddingTop: 80 }}>
                <h2 style={{ color: 'var(--error)' }}>Access Denied</h2>
                <p style={{ color: 'var(--text-secondary)', marginTop: 8 }}>Platform admin access required.</p>
            </div>
        );
    }

    useEffect(() => {
        const opts = { credentials: 'include' };
        Promise.all([
            fetch('/api/admin/stats', opts).then(r => r.json()),
            fetch('/api/admin/users', opts).then(r => r.json()),
            fetch('/api/admin/instances', opts).then(r => r.json()),
            fetch('/api/admin/payments', opts).then(r => r.json()),
            fetch('/api/admin/token-usage?days=30', opts).then(r => r.json()),
        ]).then(([s, u, i, p, t]) => {
            setStats(s);
            setUsers(u.users || []);
            setInstances(i.instances || []);
            setPayments(p);
            setTokenData(t.data || []);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, []);

    const sort = (data, col) => {
        if (!col) return data;
        return [...data].sort((a, b) => {
            const av = a[col], bv = b[col];
            if (av == null && bv == null) return 0;
            if (av == null) return 1;
            if (bv == null) return -1;
            if (typeof av === 'number') return sortDir === 'asc' ? av - bv : bv - av;
            return sortDir === 'asc' ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
        });
    };

    const handleSort = (col) => {
        if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortCol(col); setSortDir('asc'); }
    };

    const SortHeader = ({ col, children }) => (
        <th onClick={() => handleSort(col)} style={{ cursor: 'pointer', userSelect: 'none' }}>
            {children} {sortCol === col ? (sortDir === 'asc' ? '\u25b2' : '\u25bc') : ''}
        </th>
    );

    if (loading) {
        return (
            <div className="dashboard-container" style={{ textAlign: 'center', paddingTop: 80 }}>
                <p style={{ color: 'var(--text-secondary)' }}>Loading admin data...</p>
            </div>
        );
    }

    const totalTokens = (stats?.total_input_tokens || 0) + (stats?.total_output_tokens || 0);

    return (
        <div className="dashboard-container">
            <div className="dashboard-header">
                <h2 className="dashboard-title">Platform Admin</h2>
            </div>

            <div className="dashboard-cards">
                <StatCard label="Total Users" value={stats?.total_users} accent="#6c8cff" />
                <StatCard label="Active Instances" value={stats?.active_instances} accent="#4ade80" />
                <StatCard label="Total Queries" value={formatNum(stats?.total_queries)} accent="#fbbf24" />
                <StatCard label="Total Tokens" value={formatNum(totalTokens)} accent="#a78bfa" />
                <StatCard label="Query Packs Sold" value={stats?.total_purchases} accent="#f87171" />
            </div>

            <div className="dashboard-grid">
                <div className="dashboard-chart">
                    <h4>Token Usage (Last 30 Days)</h4>
                    {tokenData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <LineChart data={tokenData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3045" />
                                <XAxis dataKey="date" tick={{ fill: '#9ca0b0', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#9ca0b0', fontSize: 11 }} />
                                <Tooltip {...tooltipStyle} />
                                <Line type="monotone" dataKey="input_tokens" stroke="#6c8cff" name="Input Tokens" dot={false} />
                                <Line type="monotone" dataKey="output_tokens" stroke="#a78bfa" name="Output Tokens" dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : <div className="empty-chart"><span>No token data yet</span></div>}
                </div>

                <div className="dashboard-chart">
                    <h4>Daily Queries (Last 30 Days)</h4>
                    {tokenData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={tokenData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3045" />
                                <XAxis dataKey="date" tick={{ fill: '#9ca0b0', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#9ca0b0', fontSize: 11 }} allowDecimals={false} />
                                <Tooltip {...tooltipStyle} />
                                <Bar dataKey="queries" fill="#4ade80" name="Queries" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : <div className="empty-chart"><span>No query data yet</span></div>}
                </div>
            </div>

            <div className="dashboard-management">
                <div className="admin-tabs">
                    {['users', 'instances', 'payments'].map(tab => (
                        <button
                            key={tab}
                            className={`admin-tab${activeTab === tab ? ' active' : ''}`}
                            onClick={() => { setActiveTab(tab); setSortCol(null); }}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>

                {activeTab === 'users' && (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="admin-table">
                            <thead>
                                <tr>
                                    <SortHeader col="email">Email</SortHeader>
                                    <SortHeader col="display_name">Name</SortHeader>
                                    <SortHeader col="email_verified">Verified</SortHeader>
                                    <SortHeader col="instance_count">Instances</SortHeader>
                                    <SortHeader col="created_at">Joined</SortHeader>
                                </tr>
                            </thead>
                            <tbody>
                                {sort(users, sortCol).map(u => (
                                    <tr key={u.id}>
                                        <td>{u.email}</td>
                                        <td>{u.display_name}</td>
                                        <td>{u.email_verified ? 'Yes' : 'No'}</td>
                                        <td>{u.instance_count}</td>
                                        <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '\u2014'}</td>
                                    </tr>
                                ))}
                                {users.length === 0 && <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No users</td></tr>}
                            </tbody>
                        </table>
                    </div>
                )}

                {activeTab === 'instances' && (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="admin-table">
                            <thead>
                                <tr>
                                    <SortHeader col="name">Name</SortHeader>
                                    <SortHeader col="tier">Tier</SortHeader>
                                    <SortHeader col="status">Status</SortHeader>
                                    <SortHeader col="query_count">Queries</SortHeader>
                                    <SortHeader col="query_limit">Limit</SortHeader>
                                    <SortHeader col="member_count">Members</SortHeader>
                                    <SortHeader col="owner_email">Owner</SortHeader>
                                    <th>Addons</th>
                                    <SortHeader col="created_at">Created</SortHeader>
                                </tr>
                            </thead>
                            <tbody>
                                {sort(instances, sortCol).map(i => (
                                    <tr key={i.id}>
                                        <td>{i.name}</td>
                                        <td><span className="doc-badge">{i.tier}</span></td>
                                        <td>{i.status}</td>
                                        <td>{i.query_count}</td>
                                        <td>{i.query_limit}</td>
                                        <td>{i.member_count}</td>
                                        <td>{i.owner_email || '\u2014'}</td>
                                        <td>{i.addons.length > 0 ? i.addons.join(', ') : '\u2014'}</td>
                                        <td>{i.created_at ? new Date(i.created_at).toLocaleDateString() : '\u2014'}</td>
                                    </tr>
                                ))}
                                {instances.length === 0 && <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No instances</td></tr>}
                            </tbody>
                        </table>
                    </div>
                )}

                {activeTab === 'payments' && (
                    <div style={{ overflowX: 'auto' }}>
                        <h4 style={{ margin: '12px 0 8px', color: 'var(--text-secondary)', fontSize: 14 }}>Query Pack Purchases</h4>
                        <table className="admin-table">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Instance</th>
                                    <th>Queries Added</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {payments.purchases.map(p => (
                                    <tr key={p.id}>
                                        <td>{p.user_email}</td>
                                        <td>{p.instance_name}</td>
                                        <td>{p.queries_added}</td>
                                        <td>{p.created_at ? new Date(p.created_at).toLocaleDateString() : '\u2014'}</td>
                                    </tr>
                                ))}
                                {payments.purchases.length === 0 && <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No purchases</td></tr>}
                            </tbody>
                        </table>

                        <h4 style={{ margin: '20px 0 8px', color: 'var(--text-secondary)', fontSize: 14 }}>Subscription Events</h4>
                        <table className="admin-table">
                            <thead>
                                <tr>
                                    <th>Instance</th>
                                    <th>Event</th>
                                    <th>Details</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {payments.subscription_events.map(s => (
                                    <tr key={s.id}>
                                        <td>{s.instance_name}</td>
                                        <td>{s.event_type}</td>
                                        <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.details || '\u2014'}</td>
                                        <td>{s.created_at ? new Date(s.created_at).toLocaleDateString() : '\u2014'}</td>
                                    </tr>
                                ))}
                                {payments.subscription_events.length === 0 && <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No events</td></tr>}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
