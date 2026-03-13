import { lazy, Suspense, useState } from 'react';
import { ChatPage } from './chat';
import { Modal } from './components';

const BrowserPage = lazy(() => import('./browser').then(m => ({ default: m.BrowserPage })));
const DashboardPage = lazy(() => import('./dashboard').then(m => ({ default: m.DashboardPage })));

export default function App() {
    const [page, setPage] = useState('chat');
    const [logoutModal, setLogoutModal] = useState(false);

    return (
        <div className="app">
            <nav className="navbar">
                <div className="nav-brand">MileCore</div>
                <div className="nav-links">
                    <button className={`nav-link${page === 'chat' ? ' active' : ''}`} onClick={() => setPage('chat')}>Chat</button>
                    <button className={`nav-link${page === 'browser' ? ' active' : ''}`} onClick={() => setPage('browser')}>Database</button>
                    <button className={`nav-link${page === 'dashboard' ? ' active' : ''}`} onClick={() => setPage('dashboard')}>Dashboard</button>
                </div>
                <div className="nav-user">
                    <span className="nav-username">Dan (Admin)</span>
                    <button className="btn btn-sm" onClick={() => setLogoutModal(true)}>Log Out</button>
                </div>
            </nav>
            <div className="app-content">
                <Suspense fallback={<div className="empty-state"><div className="empty-state-sub">Loading...</div></div>}>
                    {page === 'chat' && <ChatPage />}
                    {page === 'browser' && <BrowserPage />}
                    {page === 'dashboard' && <DashboardPage />}
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
