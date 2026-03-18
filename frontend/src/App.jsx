import { lazy, Suspense, useState, useEffect } from 'react';
import { Modal } from './components';

const LandingPage = lazy(() => import('./landing').then(m => ({ default: m.LandingPage })));
const ChatPage = lazy(() => import('./chat').then(m => ({ default: m.ChatPage })));
const BrowserPage = lazy(() => import('./browser').then(m => ({ default: m.BrowserPage })));
const DashboardPage = lazy(() => import('./dashboard').then(m => ({ default: m.DashboardPage })));
const DocumentationPage = lazy(() => import('./documentation').then(m => ({ default: m.DocumentationPage })));

function SkeletonFallback() {
    return (
        <div className="skeleton-fallback">
            <div className="skeleton-bar" style={{ width: '60%' }} />
            <div className="skeleton-bar" style={{ width: '80%' }} />
            <div className="skeleton-bar" style={{ width: '45%' }} />
        </div>
    );
}

export default function App() {
    const [page, setPage] = useState(() => {
        const path = window.location.pathname;
        if (path === '/documentation' || path === '/docs') return 'documentation';
        if (path === '/database' || path === '/browser') return 'browser';
        if (path === '/dashboard') return 'dashboard';
        if (path === '/chat') return 'chat';
        return 'landing';
    });
    const [menuOpen, setMenuOpen] = useState(false);
    const [logoutModal, setLogoutModal] = useState(false);
    const [demoModal, setDemoModal] = useState(false);
    const [seedLoading, setSeedLoading] = useState(false);
    const [seedDone, setSeedDone] = useState(false);
    const [seedAlready, setSeedAlready] = useState(false);
    const [pendingCount, setPendingCount] = useState(0);
    const [personId, setPersonId] = useState(() => {
        const stored = localStorage.getItem('personId');
        return stored ? Number(stored) : 1;
    });
    const [currentUser, setCurrentUser] = useState(null);
    const [allUsers, setAllUsers] = useState([]);

    const fetchAllUsers = () => {
        fetch('/api/users/all')
            .then(r => r.json())
            .then(d => setAllUsers(d.users || []))
            .catch(() => {});
    };

    useEffect(() => { fetchAllUsers(); }, []);

    useEffect(() => {
        const pathMap = { landing: '/', chat: '/chat', browser: '/database', dashboard: '/dashboard', documentation: '/documentation' };
        const target = pathMap[page] || '/';
        if (window.location.pathname !== target) {
            window.history.pushState(null, '', target);
        }
    }, [page]);

    useEffect(() => {
        const handlePop = () => {
            const path = window.location.pathname;
            if (path === '/documentation' || path === '/docs') setPage('documentation');
            else if (path === '/database' || path === '/browser') setPage('browser');
            else if (path === '/dashboard') setPage('dashboard');
            else if (path === '/chat') setPage('chat');
            else setPage('landing');
        };
        window.addEventListener('popstate', handlePop);
        return () => window.removeEventListener('popstate', handlePop);
    }, []);

    useEffect(() => {
        fetch(`/api/user?person_id=${personId}`)
            .then(r => r.json())
            .then(d => setCurrentUser(d))
            .catch(() => {});
    }, [personId]);

    useEffect(() => {
        const fetchCount = () => {
            fetch('/api/approvals/pending-count')
                .then(r => r.json())
                .then(d => setPendingCount(d.pending_count || 0))
                .catch(() => {});
        };
        fetchCount();
        const interval = setInterval(fetchCount, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleUserSwitch = (newId) => {
        setPersonId(newId);
        localStorage.setItem('personId', String(newId));
    };

    const handleSeedDemo = async () => {
        setSeedLoading(true);
        try {
            const res = await fetch('/api/dashboard/seed-demo', { method: 'POST' });
            const data = await res.json();
            if (data.ok) {
                setSeedDone(true);
            } else if (data.already_seeded) {
                setSeedAlready(true);
                setSeedLoading(false);
                return;
            } else {
                setSeedDone(false);
                setSeedLoading(false);
                alert('Failed to seed: ' + (data.error || 'Unknown error'));
                return;
            }
        } catch (err) {
            setSeedDone(false);
            setSeedLoading(false);
            alert('Failed to seed: ' + err.message);
            return;
        }
        setSeedLoading(false);
    };

    return (
        <div className="app">
            {page !== 'landing' && (
                <nav className="navbar">
                    <button className="nav-hamburger" onClick={() => setMenuOpen(o => !o)} aria-label="Menu">
                        <span /><span /><span />
                    </button>
                    <div className={`nav-links${menuOpen ? ' open' : ''}`}>
                        <button className={`nav-link${page === 'chat' ? ' active' : ''}`} onClick={() => { setPage('chat'); setMenuOpen(false); }}>Chat{['admin','owner'].includes(currentUser?.role) && pendingCount > 0 && <span className="approval-badge">{pendingCount} pending approval{pendingCount === 1 ? '' : 's'}</span>}</button>
                        <button className={`nav-link${page === 'browser' ? ' active' : ''}`} onClick={() => { setPage('browser'); setMenuOpen(false); }}>Database</button>
                        <button className={`nav-link${page === 'dashboard' ? ' active' : ''}`} onClick={() => { setPage('dashboard'); setMenuOpen(false); }}>Dashboard</button>
                        <button className={`nav-link nav-link-docs${page === 'documentation' ? ' active' : ''}`} onClick={() => { setPage('documentation'); setMenuOpen(false); }}>Docs</button>
                    </div>
                    <div className="nav-actions">
                        <button className={`nav-link${page === 'documentation' ? ' active' : ''}`} onClick={() => setPage('documentation')}>Docs</button>
                    </div>
                </nav>
            )}
            <div className={page === 'landing' ? 'app-content-full' : 'app-content'}>
                <Suspense fallback={<SkeletonFallback />}>
                    {page === 'landing' && <LandingPage onNavigate={setPage} />}
                    {page === 'chat' && <div className="page-enter"><ChatPage personId={personId} currentUser={currentUser} allUsers={allUsers} onSwitchUser={handleUserSwitch} onDemoBannerClick={() => setDemoModal(true)} /></div>}
                    {page === 'browser' && <div className="page-enter"><BrowserPage /></div>}
                    {page === 'dashboard' && <div className="page-enter"><DashboardPage currentUser={currentUser} onRefreshUsers={fetchAllUsers} /></div>}
                    {page === 'documentation' && <div className="page-enter"><DocumentationPage /></div>}
                </Suspense>
            </div>
            <Modal open={logoutModal} onClose={() => setLogoutModal(false)} title="Nice try!">
                <p style={{ fontSize: 15, lineHeight: 1.6 }}>
                    This is a Demo. Logging out of a Demo is against the law!
                </p>
                <div className="modal-actions">
                    <button className="btn btn-primary" onClick={() => setLogoutModal(false)}>OK, I'll stay</button>
                </div>
            </Modal>
            <Modal open={demoModal} onClose={() => !seedLoading && setDemoModal(false)} title="Welcome, Hackathon Demo User!">
                {seedLoading ? (
                    <div className="seed-loading">
                        <div className="seed-spinner" />
                        <p>Seeding the database with demo data...</p>
                        <p className="seed-loading-sub">This will only take a moment.</p>
                    </div>
                ) : seedDone ? (
                    <>
                        <div className="seed-success">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                <polyline points="22 4 12 14.01 9 11.01"/>
                            </svg>
                        </div>
                        <p>Demo data has been loaded successfully! The database is now populated with sample companies, people, assets, requests, and more.</p>
                        <p>You can always reset the database by going to the <strong>Dashboard</strong> page and clicking the red <strong>"Reset Database"</strong> button.</p>
                        <div className="modal-actions">
                            <button className="btn btn-primary" onClick={() => { setDemoModal(false); setSeedDone(false); }}>Let's go!</button>
                        </div>
                    </>
                ) : seedAlready ? (
                    <>
                        <div className="seed-success">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--warning, #e67e22)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="12" y1="8" x2="12" y2="12"/>
                                <line x1="12" y1="16" x2="12.01" y2="16"/>
                            </svg>
                        </div>
                        <p>The database already contains demo data. Seeding again could cause duplicates or conflicts.</p>
                        <p>To re-seed, go to the <strong>Dashboard</strong> page and click the red <strong>"Reset Database"</strong> button first, then come back here.</p>
                        <div className="modal-actions">
                            <button className="btn btn-primary" onClick={() => { setDemoModal(false); setSeedAlready(false); }}>Got it</button>
                        </div>
                    </>
                ) : (
                    <>
                        <p>TrueCore.cloud is an AI-powered database assistant for IT site operations. Talk to it in plain English to manage assets, people, support requests, events, inventory, and more — it translates your words into database actions automatically.</p>
                        <p>This demo does <strong>not</strong> come with data preloaded, except for two users: <strong>Dan</strong> (owner) and <strong>Bob</strong> (regular user).</p>
                        <p>However, if you'd like to seed the database with dummy AI-generated entries, <a href="#" onClick={(e) => { e.preventDefault(); handleSeedDemo(); }} className="seed-link">click here</a>.</p>
                        <p>You can always reset the database by going to the <strong>Dashboard</strong> page and clicking the red <strong>"Reset Database"</strong> button to wipe all data and start from scratch.</p>
                        <div className="modal-actions">
                            <button className="btn btn-primary" onClick={() => setDemoModal(false)}>Got it!</button>
                        </div>
                    </>
                )}
            </Modal>
        </div>
    );
}
