import { lazy, Suspense, useState, useEffect } from 'react';
import { Modal } from './components';
import logo from '../static/img/milecore_logo.avif';

const ChatPage = lazy(() => import('./chat').then(m => ({ default: m.ChatPage })));
const BrowserPage = lazy(() => import('./browser').then(m => ({ default: m.BrowserPage })));
const DashboardPage = lazy(() => import('./dashboard').then(m => ({ default: m.DashboardPage })));

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
    const [page, setPage] = useState('chat');
    const [logoutModal, setLogoutModal] = useState(false);
    const [pendingCount, setPendingCount] = useState(0);
    const [personId, setPersonId] = useState(() => {
        const stored = localStorage.getItem('personId');
        return stored ? Number(stored) : 1;
    });
    const [currentUser, setCurrentUser] = useState(null);

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
                    <button className={`nav-link${page === 'chat' ? ' active' : ''}`} onClick={() => setPage('chat')}>Chat{currentUser?.role === 'admin' && pendingCount > 0 && <span className="approval-badge">{pendingCount}</span>}</button>
                    <button className={`nav-link${page === 'browser' ? ' active' : ''}`} onClick={() => setPage('browser')}>Database</button>
                    <button className={`nav-link${page === 'dashboard' ? ' active' : ''}`} onClick={() => setPage('dashboard')}>Dashboard</button>
                    <a className="nav-link" href="/docs">Documentation</a>
                </div>
                <div className="nav-brand">
                    <img src={logo} alt="Milestone Technologies" className="nav-brand-logo" />
                    <div className="nav-brand-text">
                        <span className="nav-brand-title">MileCore</span>
                        <span className="nav-brand-motto">It simply works.</span>
                    </div>
                </div>
                <div className="nav-user">
                    <span className="nav-username">{displayName}</span>
                    <button className="btn btn-sm" onClick={switchUser}>{switchLabel}</button>
                </div>
            </nav>
            <div className="app-content">
                <Suspense fallback={<SkeletonFallback />}>
                    {page === 'chat' && <div className="page-enter"><ChatPage personId={personId} /></div>}
                    {page === 'browser' && <div className="page-enter"><BrowserPage /></div>}
                    {page === 'dashboard' && <div className="page-enter"><DashboardPage currentUser={currentUser} /></div>}
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
        </div>
    );
}
