import { useState, useEffect, useRef } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell,
    ResponsiveContainer, CartesianGrid,
} from 'recharts';

const COLORS = ['#6c8cff', '#4ade80', '#f87171', '#fbbf24', '#a78bfa', '#38bdf8'];

const tooltipStyle = {
    contentStyle: { background: '#1a1d27', border: '1px solid #2d3045', borderRadius: 8, fontSize: 13 },
    labelStyle: { color: '#9ca0b0' },
};

const DEMO_FILES = [
    { name: 'companies.csv', description: '4 client & vendor companies', hint: 'Upload via chat' },
    { name: 'sites.csv', description: '3 office sites across Dublin, Austin, London', hint: 'Upload via chat' },
    { name: 'rooms.csv', description: '10 rooms — server rooms, offices, conference rooms', hint: 'Upload via chat' },
    { name: 'people.csv', description: '12 staff with roles, departments, sites', hint: 'Upload via chat' },
    { name: 'assets.csv', description: '15 laptops, monitors, switches, printers, APs', hint: 'Upload via chat' },
    { name: 'requests.csv', description: '12 support tickets in various statuses', hint: 'Upload via chat' },
    { name: 'technical_issues.csv', description: '8 known issues with symptoms & resolutions', hint: 'Upload via chat' },
    { name: 'events.csv', description: '6 vendor visits, maintenance, training sessions', hint: 'Upload via chat' },
    { name: 'inventory_items.csv', description: '10 spare parts, cables, toner, consumables', hint: 'Upload via chat' },
    { name: 'demo_full_import.xlsx', description: 'All tables in one workbook', hint: 'Use Import & Merge' },
];

const CARD_ACCENTS = {
    'Active Assets': '#6c8cff',
    'Open Requests': '#4ade80',
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

export function DashboardPage({ currentUser }) {
    const [overview, setOverview] = useState(null);
    const [assets, setAssets] = useState([]);
    const [issues, setIssues] = useState({ by_status: [], by_severity: [] });
    const [staff, setStaff] = useState([]);
    const [refreshedAt, setRefreshedAt] = useState(null);
    const [reportStatus, setReportStatus] = useState(null);
    const [importing, setImporting] = useState(false);
    const importRef = useRef(null);

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

    useEffect(() => { loadDashboard(); }, []);

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
                <StatCard label="Open Requests" value={overview?.open_requests} accent={CARD_ACCENTS['Open Requests']} />
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

                <ChartBox title="Requests by Status">
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
                    Repository last updated at: {new Date(overview.last_push).toLocaleString()}
                </p>
            )}

            <div className="dashboard-management">
                <div className="dashboard-management-title">Dummy Files for Demo</div>
                <div className="dashboard-management-hint">
                    Download sample data to test the chatbot (CSV) or Import &amp; Merge (XLSX). Feel free to modify these files or use your own.
                </div>
                <div className="demo-files-grid">
                    {DEMO_FILES.map(f => (
                        <a key={f.name} href={`/dummy_files/${f.name}`} download className="btn btn-sm" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', textAlign: 'left', gap: '0.15rem' }}>
                            <span style={{ fontWeight: 600 }}>{f.name}</span>
                            <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>{f.description}</span>
                            <span style={{ fontSize: '0.7rem', opacity: 0.5 }}>{f.hint}</span>
                        </a>
                    ))}
                </div>
            </div>

            <div className="dashboard-management">
                <div className="dashboard-management-title">Database Management</div>
                <div className="dashboard-management-row">
                    <a href="/api/tables/download" download className="btn btn-sm">Download .db</a>
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
                        accept=".xlsx,.db"
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
                <div className="dashboard-management-title">Demo-only</div>
                <div className="dashboard-management-row">
                    {currentUser?.role === 'admin' && (
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
