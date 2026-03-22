import { lazy, Suspense, useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import { AuthPage } from './auth';
import { InstanceSelector } from './instance-selector';

const LandingPage = lazy(() => import('./landing').then(m => ({ default: m.LandingPage })));
const ChatPage = lazy(() => import('./chat').then(m => ({ default: m.ChatPage })));
const BrowserPage = lazy(() => import('./browser').then(m => ({ default: m.BrowserPage })));
const DashboardPage = lazy(() => import('./dashboard').then(m => ({ default: m.DashboardPage })));
const DocumentationPage = lazy(() => import('./documentation').then(m => ({ default: m.DocumentationPage })));
const AdminPage = lazy(() => import('./admin').then(m => ({ default: m.AdminPage })));

function SkeletonFallback() {
    return (
        <div className="skeleton-fallback">
            <div className="skeleton-bar" style={{ width: '60%' }} />
            <div className="skeleton-bar" style={{ width: '80%' }} />
            <div className="skeleton-bar" style={{ width: '45%' }} />
        </div>
    );
}

function AppContent() {
    const { isAuthenticated, loading, instanceId, user, checkAuth } = useAuth();

    const [page, setPage] = useState(() => {
        const path = window.location.pathname;
        if (path === '/documentation' || path === '/docs') return 'documentation';
        if (path === '/database' || path === '/browser') return 'browser';
        if (path === '/dashboard') return 'dashboard';
        if (path === '/admin') return 'admin';
        if (path === '/chat') return 'chat';
        if (path === '/login') return 'login';
        return 'landing';
    });
    const [menuOpen, setMenuOpen] = useState(false);
    const [pendingCount, setPendingCount] = useState(0);
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        const pathMap = {
            landing: '/', login: '/login', chat: '/chat',
            browser: '/database', dashboard: '/dashboard', admin: '/admin', documentation: '/documentation',
        };
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
            else if (path === '/admin') setPage('admin');
            else if (path === '/chat') setPage('chat');
            else if (path === '/login') setPage('login');
            else setPage('landing');
        };
        window.addEventListener('popstate', handlePop);
        return () => window.removeEventListener('popstate', handlePop);
    }, []);

    // Fetch current user info from the instance when authenticated + instance selected
    useEffect(() => {
        if (!isAuthenticated || !instanceId) {
            setCurrentUser(null);
            return;
        }
        fetch('/api/user', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(d => d && setCurrentUser(d))
            .catch(() => {});
    }, [isAuthenticated, instanceId]);

    // Poll pending approvals
    useEffect(() => {
        if (!isAuthenticated || !instanceId) return;
        const fetchCount = () => {
            fetch('/api/approvals/pending-count', { credentials: 'include' })
                .then(r => r.ok ? r.json() : { pending_count: 0 })
                .then(d => setPendingCount(d.pending_count || 0))
                .catch(() => {});
        };
        fetchCount();
        const interval = setInterval(fetchCount, 30000);
        return () => clearInterval(interval);
    }, [isAuthenticated, instanceId]);

    // Show loading spinner while checking auth
    if (loading) {
        return <SkeletonFallback />;
    }

    // Landing page — always accessible
    if (page === 'landing' && !isAuthenticated) {
        return (
            <div className="app">
                <div className="app-content-full">
                    <Suspense fallback={<SkeletonFallback />}>
                        <LandingPage onNavigate={(p) => {
                            if (p === 'chat' || p === 'login') {
                                setPage('login');
                            } else {
                                setPage(p);
                            }
                        }} />
                    </Suspense>
                </div>
            </div>
        );
    }

    // Login / Signup page
    if (!isAuthenticated || page === 'login') {
        return (
            <div className="app">
                <div className="app-content-full">
                    <AuthPage onSuccess={() => { checkAuth(); setPage('chat'); }} />
                </div>
            </div>
        );
    }

    // Instance selector — shown when authenticated but no instance selected
    if (!instanceId) {
        return (
            <div className="app">
                <div className="app-content-full">
                    <InstanceSelector onInstanceSelected={() => setPage('chat')} />
                </div>
            </div>
        );
    }

    // If on landing while authenticated, redirect to chat
    if (page === 'landing') {
        setPage('chat');
        return null;
    }

    // Main app — authenticated with instance selected
    const isAdmin = ['admin', 'owner'].includes(currentUser?.role);

    return (
        <div className="app">
            <nav className="navbar">
                <button className="nav-hamburger" onClick={() => setMenuOpen(o => !o)} aria-label="Menu">
                    <span /><span /><span />
                </button>
                <div className={`nav-links${menuOpen ? ' open' : ''}`}>
                    <button className={`nav-link${page === 'chat' ? ' active' : ''}`} onClick={() => { setPage('chat'); setMenuOpen(false); }}>Chat{isAdmin && pendingCount > 0 && <span className="approval-badge">{pendingCount} pending approval{pendingCount === 1 ? '' : 's'}</span>}</button>
                    <button className={`nav-link${page === 'browser' ? ' active' : ''}`} onClick={() => { setPage('browser'); setMenuOpen(false); }}>Database</button>
                    <button className={`nav-link${page === 'dashboard' ? ' active' : ''}`} onClick={() => { setPage('dashboard'); setMenuOpen(false); }}>Dashboard</button>
                    <button className={`nav-link nav-link-docs${page === 'documentation' ? ' active' : ''}`} onClick={() => { setPage('documentation'); setMenuOpen(false); }}>Docs</button>
                    {user?.email === 'gocandan@gmail.com' && <button className={`nav-link${page === 'admin' ? ' active' : ''}`} onClick={() => { setPage('admin'); setMenuOpen(false); }}>Admin</button>}
                </div>
                <div className="nav-actions">
                    <button className={`nav-link${page === 'documentation' ? ' active' : ''}`} onClick={() => setPage('documentation')}>Docs</button>
                </div>
            </nav>
            <div className="app-content">
                <Suspense fallback={<SkeletonFallback />}>
                    {page === 'chat' && <div className="page-enter"><ChatPage currentUser={currentUser} /></div>}
                    {page === 'browser' && <div className="page-enter"><BrowserPage /></div>}
                    {page === 'dashboard' && <div className="page-enter"><DashboardPage currentUser={currentUser} /></div>}
                    {page === 'admin' && <div className="page-enter"><AdminPage /></div>}
                    {page === 'documentation' && <div className="page-enter"><DocumentationPage /></div>}
                </Suspense>
            </div>
        </div>
    );
}

export default function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
}
