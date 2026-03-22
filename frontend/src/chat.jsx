import { useState, useEffect, useRef } from 'react';
import Markdown from 'react-markdown';
import { Modal } from './components';
import profilePic1 from '../static/img/profile_pic_1.jpg';
import profilePic2 from '../static/img/profile_pic_2.jpg';
import profilePic3 from '../static/img/profile_pic_3.jpg';

const profilePics = [profilePic1, profilePic2, profilePic3];

function ThinkingDots() {
    return (
        <div className="thinking-dots">
            <span /><span /><span />
        </div>
    );
}

function AdminStarIcon() {
    return (
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 2.75l2.85 5.77 6.37.93-4.61 4.49 1.09 6.35L12 17.3l-5.7 2.99 1.09-6.35-4.61-4.49 6.37-.93L12 2.75z" />
        </svg>
    );
}

function SqlBlock({ operations }) {
    const [open, setOpen] = useState(false);
    if (!operations || operations.length === 0) return null;

    const sqlCount = operations.filter(op => op.tool !== 'send_email').length;
    const emailCount = operations.filter(op => op.tool === 'send_email').length;
    const label = [
        sqlCount > 0 && `${sqlCount} SQL quer${sqlCount === 1 ? 'y' : 'ies'}`,
        emailCount > 0 && `${emailCount} email${emailCount === 1 ? '' : 's'} sent`,
    ].filter(Boolean).join(', ');

    return (
        <div className="sql-block">
            <button className={`sql-toggle${open ? ' open' : ''}`} onClick={() => setOpen(!open)}>
                <span className="chevron">{'\u25B6'}</span> {label}
            </button>
            {open && (
                <div className="sql-content">
                    {operations.map((op, i) => (
                        <div key={i} style={{ marginBottom: 10 }}>
                            {op.tool === 'send_email' ? (
                                <div className="sql-explanation">{op.action}</div>
                            ) : (
                                <>
                                    {(op.explanation || op.action) && <div className="sql-explanation">{op.explanation || op.action}</div>}
                                    {op.sql && <pre className="sql-query">{op.sql}</pre>}
                                </>
                            )}
                            {op.result && !op.result.error && (
                                <div className="sql-result">
                                    {op.tool === 'send_email' ? 'Sent' : op.result.rowcount !== undefined ? `${op.result.rowcount} row(s)` : 'OK'}
                                </div>
                            )}
                            {op.result && op.result.error && (
                                <div className="sql-error-result">{op.result.error}</div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function DownloadBlock({ files }) {
    if (!files || files.length === 0) return null;
    return (
        <>
            {files.map((f, i) => {
                const res = f.result || {};
                const sheets = res.sheets || [];
                const sheetLabel = sheets.length === 1 ? '1 sheet' : `${sheets.length} sheets`;
                return (
                    <div key={i} className="download-block">
                        <div className="download-block-info">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                <polyline points="14 2 14 8 20 8"/>
                            </svg>
                            <div className="download-block-meta">
                                <span className="download-block-filename">{res.filename || 'file.xlsx'}</span>
                                <span className="download-block-detail">{sheetLabel}</span>
                            </div>
                        </div>
                        <a
                            className="download-block-btn"
                            href={res.download_url || `/api/downloads/${res.file_id}`}
                            download
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                <polyline points="7 10 12 15 17 10"/>
                                <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                            Download
                        </a>
                    </div>
                );
            })}
        </>
    );
}

function FileAttachment({ file }) {
    return (
        <div className="file-attachment">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span className="file-attachment-name">{file.name}</span>
            <span className="file-attachment-format">{file.format}</span>
        </div>
    );
}

function ChatMessage({ role, text, sql, files, file, timestamp }) {
    const cls = role === 'user' ? 'message message-user'
        : role === 'error' ? 'message message-error'
        : role === 'loading' ? 'message message-loading'
        : 'message message-assistant';

    return (
        <div className="message-content">
            <div className={cls}>
                {file && <FileAttachment file={file} />}
                {role === 'loading' ? <ThinkingDots /> : role === 'assistant' ? <Markdown>{text}</Markdown> : text}
                {role === 'assistant' && <DownloadBlock files={files} />}
                {role === 'assistant' && <SqlBlock operations={sql} />}
            </div>
            {timestamp && <div className="message-timestamp">{timestamp}</div>}
        </div>
    );
}

const PROMPTS = [
    { text: 'How many Dell Latitude laptops do we have out of warranty?', color: '#7dd3fc' },
    { text: 'Add PTO for Michael, from 1st of May until the 14th', color: '#c084fc' },
    { text: 'Send HP vendor an email, asking them if they are available to come on site on Tuesday', color: '#4ade80' },
    { text: 'How do I get access to the network-security Slack channel?', color: '#22d3ee' },
    { text: 'Add Martha as the AV Technician for the Paris Office. Her email is martha@truecore.cloud', color: '#facc15' },
    { text: 'Add 6 hours of work for Jim today, on the issue we have with the Cisco Access Points', color: '#fb923c' },
    { text: 'Does the town hall in the canteen today need audio/video support?', color: '#f472b6' },
];

export function ChatPage({ currentUser }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [homeSiteChecked, setHomeSiteChecked] = useState(false);
    const [sessions, setSessions] = useState([]);
    const [pendingFile, setPendingFile] = useState(null);
    const [badgeIndex, setBadgeIndex] = useState(0);
    const [usage, setUsage] = useState(null);
    const messagesEnd = useRef(null);
    const fileRef = useRef(null);
    const streamRafRef = useRef(null);
    const userProfilePic = profilePics[0];
    const assistantProfilePic = profilePics[2];
    const sidebarDisplayName = currentUser?.display_name || '...';
    const sidebarJobTitle = currentUser?.job_title || '';
    const isAdmin = ['admin', 'owner'].includes(currentUser?.role);

    const loadSessions = () => {
        fetch('/api/sessions', { credentials: 'include' }).then(r => r.json()).then(d => setSessions(d.sessions || [])).catch(() => {});
    };

    const loadUsage = () => {
        fetch('/api/dashboard/usage', { credentials: 'include' }).then(r => r.ok ? r.json() : null).then(d => d && setUsage(d)).catch(() => {});
    };

    useEffect(() => {
        setSessionId(null);
        setMessages([]);
        loadSessions();
        loadUsage();
    }, []);

    useEffect(() => {
        loadSessions();
        setHomeSiteChecked(true);
    }, []);

    useEffect(() => {
        if (messagesEnd.current) {
            messagesEnd.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, loading]);

    useEffect(() => {
        if (messages.length > 0) return;
        const id = setInterval(() => {
            setBadgeIndex(prev => (prev + 1) % PROMPTS.length);
        }, 5000);
        return () => clearInterval(id);
    }, [messages.length]);

    useEffect(() => {
        if (sidebarOpen) document.body.classList.add('sidebar-open');
        else document.body.classList.remove('sidebar-open');
        return () => document.body.classList.remove('sidebar-open');
    }, [sidebarOpen]);

    const loadSession = async (sid) => {
        try {
            const res = await fetch(`/api/sessions/${sid}`);
            const data = await res.json();
            setSessionId(sid);
            setMessages(data.messages || []);
            setSidebarOpen(false);
        } catch {}
    };

    const startNewChat = () => {
        setSessionId(null);
        setMessages([]);
        setSidebarOpen(false);
    };

    const sendMessage = async () => {
        const text = input.trim();
        if ((!text && !pendingFile) || loading) return;

        const fileToUpload = pendingFile;
        const displayText = text || '';
        setInput('');
        setPendingFile(null);
        const userMsg = { role: 'user', text: displayText, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
        if (fileToUpload) {
            const ext = fileToUpload.name.split('.').pop().toUpperCase();
            userMsg.file = { name: fileToUpload.name, format: ext };
        }
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            let messageToSend = text;
            if (fileToUpload) {
                const isCSV = fileToUpload.name.toLowerCase().endsWith('.csv');
                const formData = new FormData();
                formData.append('file', fileToUpload);

                if (isCSV) {
                    const uploadRes = await fetch('/api/upload/stage', { method: 'POST', body: formData });
                    const uploadData = await uploadRes.json();
                    if (!uploadRes.ok) throw new Error(uploadData.detail || 'Upload failed');

                    const samplePreview = uploadData.sample_rows.map(r => JSON.stringify(r)).join('\n');
                    const stagingSummary = `Import this CSV file (file_id: ${uploadData.file_id}).\n` +
                        `Filename: ${uploadData.filename}\n` +
                        `Columns: ${uploadData.headers.join(', ')}\n` +
                        `Total rows: ${uploadData.total_rows}\n` +
                        `Sample data:\n${samplePreview}`;
                    messageToSend = text ? `${stagingSummary}\n\nUser note: ${text}` : stagingSummary;
                } else {
                    const uploadRes = await fetch('/api/upload/file', { method: 'POST', body: formData });
                    const uploadData = await uploadRes.json();
                    if (!uploadRes.ok) throw new Error(uploadData.detail || 'Upload failed');

                    const attachInfo = `[Attached file: ${uploadData.filename} (file_id: ${uploadData.file_id}, type: ${uploadData.content_type})]`;
                    messageToSend = text ? `${attachInfo}\n\n${text}` : attachInfo;
                }
            }

            const res = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageToSend, session_id: sessionId }),
                credentials: 'include',
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Request failed');
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let assistantText = '';
            let sqlOps = [];
            let files = [];
            let started = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop();

                for (const part of parts) {
                    if (!part.trim()) continue;
                    let eventType = '', eventData = '';
                    for (const line of part.split('\n')) {
                        if (line.startsWith('event: ')) eventType = line.slice(7);
                        else if (line.startsWith('data: ')) eventData = line.slice(6);
                    }
                    if (!eventData) continue;
                    const data = JSON.parse(eventData);

                    if (eventType === 'session') {
                        setSessionId(data.session_id);
                    } else if (eventType === 'token') {
                        if (!started) {
                            started = true;
                            setLoading(false);
                            setMessages(prev => [...prev, { role: 'assistant', text: '', sql: [], timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
                        }
                        assistantText += data.text;
                        if (!streamRafRef.current) {
                            streamRafRef.current = requestAnimationFrame(() => {
                                setMessages(prev => {
                                    const next = [...prev];
                                    next[next.length - 1] = { ...next[next.length - 1], text: assistantText };
                                    return next;
                                });
                                streamRafRef.current = null;
                            });
                        }
                    } else if (eventType === 'sql') {
                        sqlOps.push(data);
                    } else if (eventType === 'file') {
                        files.push(data);
                    } else if (eventType === 'done') {
                        if (streamRafRef.current) {
                            cancelAnimationFrame(streamRafRef.current);
                            streamRafRef.current = null;
                        }
                        const queriesConsumed = data.queries_consumed || 1;
                        const creditNote = queriesConsumed > 1 ? `\n\n*This query used ${queriesConsumed} credits due to complexity.*` : '';
                        if (!started) {
                            setLoading(false);
                            setMessages(prev => [...prev, { role: 'assistant', text: assistantText + creditNote, sql: sqlOps, files, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
                        } else {
                            setMessages(prev => {
                                const next = [...prev];
                                next[next.length - 1] = { ...next[next.length - 1], text: assistantText + creditNote, sql: sqlOps, files };
                                return next;
                            });
                        }
                        loadSessions();
                    }
                }
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: 'error', text: err.message }]);
        } finally {
            setLoading(false);
            loadUsage();
        }
    };

    const ALLOWED_EXTENSIONS = ['.csv', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.bmp', '.tiff', '.tif', '.svg'];

    const stageFile = (file) => {
        if (!file) return;
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            setMessages(prev => [...prev, { role: 'error', text: `File type not supported. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}` }]);
            return;
        }
        setPendingFile(file);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const prompt = PROMPTS[badgeIndex];

    return (
        <div className="chat-layout">
            <div className={`sidebar-backdrop${sidebarOpen ? ' visible' : ''}`} onClick={() => setSidebarOpen(false)} />
            <div className={`session-sidebar${sidebarOpen ? ' open' : ''}`}>
                <div className="sidebar-header">
                    <h3>Conversations</h3>
                    <button className="btn btn-sm btn-primary" onClick={startNewChat}>+ New</button>
                </div>
                <div className="sidebar-list">
                    {sessions.map(s => (
                        <div
                            key={s.id}
                            className={`session-item${s.id === sessionId ? ' active' : ''}`}
                            onClick={() => loadSession(s.id)}
                        >
                            <span className="session-title">{s.title || 'New conversation'}</span>
                        </div>
                    ))}
                    {sessions.length === 0 && (
                        <div className="sidebar-empty">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                            </svg>
                            <span>No conversations yet. Start one!</span>
                        </div>
                    )}
                </div>
                <div className="sidebar-user">
                    <div className="sidebar-user-header">
                        <img src={userProfilePic} alt={sidebarDisplayName} className="sidebar-user-avatar" />
                        <div className="sidebar-user-meta">
                            <div className="sidebar-user-name-row">
                                <span className="sidebar-user-name">{sidebarDisplayName}</span>
                                {sidebarJobTitle && <span className="sidebar-user-title">({sidebarJobTitle})</span>}
                                {isAdmin && (
                                    <span className="sidebar-user-star" title="Admin" aria-label="Admin">
                                        <AdminStarIcon />
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                    {usage && (
                        <div className="sidebar-usage">
                            <div className="sidebar-usage-bar">
                                <div className="sidebar-usage-fill" style={{ width: `${Math.min(100, (usage.query_count / usage.query_limit) * 100)}%` }} />
                            </div>
                            <span className="sidebar-usage-text">
                                {usage.queries_remaining} / {usage.query_limit} queries left
                                {usage.seat_count > 1 && ` (${usage.seat_count} users)`}
                            </span>
                            {usage.query_pool_reset_at && (
                                <span className="sidebar-usage-reset">
                                    Resets {new Date(usage.query_pool_reset_at).toLocaleDateString()}
                                </span>
                            )}
                        </div>
                    )}
                    <div className="sidebar-user-row">
                        <button className="btn btn-sm" onClick={() => setSettingsOpen(true)} title="Settings">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="3"/>
                                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
            <div className="chat-container">
                <button className="sidebar-toggle-btn" onClick={() => setSidebarOpen(o => !o)} aria-label="Toggle sidebar">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/>
                    </svg>
                </button>
                <div className="chat-messages">
                    {messages.length === 0 && homeSiteChecked && (
                        <div className="empty-state">
                            <div className="empty-state-hero">
                                <div className="empty-state-brand-row">
                                    <div className="empty-state-brand">TrueCore.cloud</div>
                                    <span className="empty-state-divider" aria-hidden="true">|</span>
                                    <div className="empty-state-motto">It simply works.</div>
                                </div>
                                <div className="empty-state-sub">Try asking...</div>
                            </div>
                            <div className="empty-state-badge-slot">
                                <div className="capability-badges-row" key={badgeIndex}>
                                    <span className="capability-badge" style={{ borderColor: prompt.color }}>{prompt.text}</span>
                                </div>
                            </div>
                        </div>
                    )}
                    {messages.map((m, i) => {
                        if (m.role === 'user') {
                            return (
                                <div key={i} className="message-row message-row-user">
                                    <ChatMessage role={m.role} text={m.text} sql={m.sql} file={m.file} timestamp={m.timestamp} />
                                    <img src={userProfilePic} alt="You" className="profile-pic" />
                                </div>
                            );
                        }
                        if (m.role === 'assistant') {
                            return (
                                <div key={i} className="message-row message-row-assistant">
                                    <img src={assistantProfilePic} alt="AI" className="profile-pic" />
                                    <ChatMessage role={m.role} text={m.text} sql={m.sql} files={m.files} timestamp={m.timestamp} />
                                </div>
                            );
                        }
                        return <ChatMessage key={i} role={m.role} text={m.text} sql={m.sql} />;
                    })}
                    {loading && (
                        <div className="message-row message-row-assistant">
                            <img src={assistantProfilePic} alt="AI" className="profile-pic" />
                            <ChatMessage role="loading" />
                        </div>
                    )}
                    <div ref={messagesEnd} />
                </div>
                <div className="chat-input-container">
                    <div className="chat-input-card">
                        <div className="chat-input-wrapper">
                            <textarea
                                className="chat-input"
                                placeholder="Type a message..."
                                aria-label="Message input"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                rows={1}
                                disabled={loading}
                            />
                            <button
                                className="upload-btn"
                                onClick={() => fileRef.current && fileRef.current.click()}
                                disabled={loading}
                                title="Attach image"
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                                </svg>
                            </button>
                            <input
                                ref={fileRef}
                                type="file"
                                accept=".csv,.jpg,.jpeg,.png,.gif,.webp,.avif,.bmp,.tiff,.tif,.svg"
                                style={{ display: 'none' }}
                                onChange={(e) => { stageFile(e.target.files[0]); e.target.value = ''; }}
                            />
                            {pendingFile && (
                                <div className="file-chip">
                                    <span className="file-chip-name">{pendingFile.name}</span>
                                    <button className="file-chip-dismiss" onClick={() => setPendingFile(null)} aria-label="Remove file">&times;</button>
                                </div>
                            )}
                            <button
                                className="send-btn"
                                onClick={sendMessage}
                                disabled={loading || (!input.trim() && !pendingFile)}
                                title="Send message"
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="22" y1="2" x2="11" y2="13"/>
                                    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <Modal open={settingsOpen} onClose={() => setSettingsOpen(false)} title="Settings">
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                    Settings will be available in a future update.
                </p>
                <div className="modal-actions">
                    <button className="btn btn-primary" onClick={() => setSettingsOpen(false)}>OK</button>
                </div>
            </Modal>
        </div>
    );
}
