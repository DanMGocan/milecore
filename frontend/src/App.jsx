import { lazy, Suspense, useState, useEffect } from 'react';
import { Modal } from './components';

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
        return 'chat';
    });
    const [logoutModal, setLogoutModal] = useState(false);
    const [demoModal, setDemoModal] = useState(false);
    const [pendingCount, setPendingCount] = useState(0);
    const [personId, setPersonId] = useState(() => {
        const stored = localStorage.getItem('personId');
        return stored ? Number(stored) : 1;
    });
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        const pathMap = { chat: '/', browser: '/database', dashboard: '/dashboard', documentation: '/documentation' };
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
            else setPage('chat');
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

    const switchUser = () => {
        const newId = personId === 1 ? 2 : 1;
        setPersonId(newId);
        localStorage.setItem('personId', String(newId));
    };

    const displayName = currentUser
        ? `${currentUser.display_name} (${currentUser.role.charAt(0).toUpperCase() + currentUser.role.slice(1)})`
        : '...';
    const switchLabel = personId === 1 ? 'Switch to Bob' : 'Switch to Dan';

    return (
        <div className="app">
            <nav className="navbar">
                <div className="nav-links">
                    <button className={`nav-link${page === 'chat' ? ' active' : ''}`} onClick={() => setPage('chat')}>Chat{currentUser?.role === 'admin' && pendingCount > 0 && <span className="approval-badge">{pendingCount} pending approval{pendingCount === 1 ? '' : 's'}</span>}</button>
                    <button className={`nav-link${page === 'browser' ? ' active' : ''}`} onClick={() => setPage('browser')}>Database</button>
                    <button className={`nav-link${page === 'dashboard' ? ' active' : ''}`} onClick={() => setPage('dashboard')}>Dashboard</button>
                    <button className={`nav-link${page === 'documentation' ? ' active' : ''}`} onClick={() => setPage('documentation')}>Docs</button>
                </div>
            </nav>
            <div className="demo-banner" onClick={() => setDemoModal(true)}>
                Are you a Demo user, from the Milestone Hackathon? Please click me first!
            </div>
            <div className="app-content">
                <Suspense fallback={<SkeletonFallback />}>
                    {page === 'chat' && <div className="page-enter"><ChatPage personId={personId} displayName={displayName} switchLabel={switchLabel} onSwitchUser={switchUser} /></div>}
                    {page === 'browser' && <div className="page-enter"><BrowserPage /></div>}
                    {page === 'dashboard' && <div className="page-enter"><DashboardPage currentUser={currentUser} /></div>}
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
            <Modal open={demoModal} onClose={() => setDemoModal(false)} title="Welcome, Hackathon Demo User!">
                <p>MileCore is an AI-powered database assistant for IT site operations. Talk to it in plain English to manage assets, people, support requests, events, inventory, and more — it translates your words into database actions automatically.</p>
                <p>This demo comes with a <strong>fully seeded database</strong> already loaded with sample data (people, assets, issues, events, etc.) so you can start exploring right away.</p>
                <p>If you want a fresh start, go to the <strong>Dashboard</strong> page and click the red <strong>"Reset Database"</strong> button at the bottom to wipe all data and start from scratch.</p>
                <div className="modal-actions">
                    <button className="btn btn-primary" onClick={() => setDemoModal(false)}>Got it!</button>
                </div>
            </Modal>
        </div>
    );
}
