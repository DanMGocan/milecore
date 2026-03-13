import { useState, useEffect } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell,
    ResponsiveContainer, CartesianGrid,
} from 'recharts';

const COLORS = ['#6c8cff', '#4ade80', '#f87171', '#fbbf24', '#a78bfa', '#38bdf8'];

const tooltipStyle = {
    contentStyle: { background: '#1a1d27', border: '1px solid #2d3045', borderRadius: 8, fontSize: 13 },
    labelStyle: { color: '#9ca0b0' },
};

function StatCard({ label, value }) {
    return (
        <div className="dashboard-card">
            <div className="dashboard-card-value">{value ?? '—'}</div>
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

export function DashboardPage() {
    const [overview, setOverview] = useState(null);
    const [assets, setAssets] = useState([]);
    const [issues, setIssues] = useState({ by_status: [], by_severity: [] });
    const [staff, setStaff] = useState([]);

    useEffect(() => {
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
        }).catch(console.error);
    }, []);

    return (
        <div className="dashboard-container">
            <h2 className="dashboard-title">Dashboard</h2>

            <div className="dashboard-cards">
                <StatCard label="Active Assets" value={overview?.active_assets} />
                <StatCard label="Open Requests" value={overview?.open_requests} />
                <StatCard label="Open Issues" value={overview?.open_issues} />
                <StatCard label="Events This Week" value={overview?.events_this_week} />
                <StatCard label="Flagged Important" value={overview?.important_items} />
            </div>

            <div className="dashboard-grid">
                <ChartBox title="Assets Added Over Time">
                    {assets.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={assets}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3045" />
                                <XAxis dataKey="date" tick={{ fill: '#9ca0b0', fontSize: 11 }} />
                                <YAxis tick={{ fill: '#9ca0b0', fontSize: 11 }} allowDecimals={false} />
                                <Tooltip {...tooltipStyle} />
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
                                <Tooltip {...tooltipStyle} />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : <EmptyChart />}
                </ChartBox>

                <ChartBox title="Requests by Status">
                    {issues.by_status.length > 0 ? (
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={issues.by_status} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3045" />
                                <XAxis type="number" tick={{ fill: '#9ca0b0', fontSize: 11 }} allowDecimals={false} />
                                <YAxis type="category" dataKey="status" tick={{ fill: '#9ca0b0', fontSize: 11 }} width={100} />
                                <Tooltip {...tooltipStyle} />
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
                                <Tooltip {...tooltipStyle} />
                                <Bar dataKey="count" fill="#a78bfa" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : <EmptyChart />}
                </ChartBox>
            </div>
        </div>
    );
}

function EmptyChart() {
    return (
        <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            No data yet
        </div>
    );
}
