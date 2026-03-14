import { useState, useEffect, useRef } from 'react';
import Markdown from 'react-markdown';
import logo from '../static/img/milecore_logo.avif';
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
                                    {op.explanation && <div className="sql-explanation">{op.explanation}</div>}
                                    <pre className="sql-query">{op.sql}</pre>
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

function ChatMessage({ role, text, sql, file, timestamp }) {
    const cls = role === 'user' ? 'message message-user'
        : role === 'error' ? 'message message-error'
        : role === 'loading' ? 'message message-loading'
        : 'message message-assistant';

    return (
        <div>
            <div className={cls}>
                {file && <FileAttachment file={file} />}
                {role === 'loading' ? <ThinkingDots /> : role === 'assistant' ? <Markdown>{text}</Markdown> : text}
                {role === 'assistant' && <SqlBlock operations={sql} />}
            </div>
            {timestamp && <div className="message-timestamp">{timestamp}</div>}
        </div>
    );
}

const BADGES = [
    { text: 'Add People', color: '#facc15' },
    { text: 'Manage Assets', color: '#7dd3fc' },
    { text: 'Send Emails', color: '#4ade80' },
    { text: 'Track Issues', color: '#f87171' },
    { text: 'Log Work', color: '#c084fc' },
    { text: 'Import CSV', color: '#fb923c' },
    { text: 'Share Knowledge', color: '#22d3ee' },
    { text: 'Manage Inventory', color: '#f472b6' },
    { text: 'Schedule Events', color: '#a3e635' },
    { text: 'Track Vendors', color: '#fbbf24' },
];

export function ChatPage({ personId = 1 }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [homeSiteChecked, setHomeSiteChecked] = useState(false);
    const [sessions, setSessions] = useState([]);
    const [pendingFile, setPendingFile] = useState(null);
    const [badgeIndex, setBadgeIndex] = useState(0);
    const messagesEnd = useRef(null);
    const fileRef = useRef(null);
    const [pics] = useState(() => {
        const indices = [0, 1, 2];
        const aiIdx = indices[Math.floor(Math.random() * 3)];
        const remaining = indices.filter(i => i !== aiIdx);
        const userIdx = remaining[Math.floor(Math.random() * remaining.length)];
        return { ai: aiIdx, user: userIdx };
    });

    const loadSessions = () => {
        fetch(`/api/sessions?person_id=${personId}`).then(r => r.json()).then(d => setSessions(d.sessions || [])).catch(() => {});
    };

    useEffect(() => {
        setSessionId(null);
        setMessages([]);
        loadSessions();
    }, [personId]);

    useEffect(() => {
        loadSessions();
        fetch('/api/home-site')
            .then(res => res.json())
            .then(data => {
                if (!data.home_site) {
                    setMessages([{
                        role: 'assistant',
                        text: "Welcome to MileCore! Before we get started, I need to know which site this instance is for. What's the client name and city? (e.g., **Workday Dublin** or **Google Paris**)",
                    }]);
                }
                setHomeSiteChecked(true);
            })
            .catch(() => setHomeSiteChecked(true));
    }, []);

    useEffect(() => {
        if (messagesEnd.current) {
            messagesEnd.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, loading]);

    useEffect(() => {
        if (messages.length > 0) return;
        const id = setInterval(() => {
            setBadgeIndex(prev => (prev + 1) % BADGES.length);
        }, 3000);
        return () => clearInterval(id);
    }, [messages.length]);

    const loadSession = async (sid) => {
        try {
            const res = await fetch(`/api/sessions/${sid}`);
            const data = await res.json();
            setSessionId(sid);
            setMessages(data.messages || []);
        } catch {}
    };

    const startNewChat = () => {
        setSessionId(null);
        setMessages([]);
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
                const formData = new FormData();
                formData.append('file', fileToUpload);
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
            }

            const res = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageToSend, session_id: sessionId, person_id: personId }),
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
                        setMessages(prev => {
                            const next = [...prev];
                            next[next.length - 1] = { ...next[next.length - 1], text: assistantText };
                            return next;
                        });
                    } else if (eventType === 'sql') {
                        sqlOps.push(data);
                    } else if (eventType === 'done') {
                        if (!started) {
                            setLoading(false);
                            setMessages(prev => [...prev, { role: 'assistant', text: assistantText, sql: sqlOps, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
                        } else {
                            setMessages(prev => {
                                const next = [...prev];
                                next[next.length - 1] = { ...next[next.length - 1], sql: sqlOps };
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
        }
    };

    const stageFile = (file) => {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.csv')) {
            setMessages(prev => [...prev, { role: 'error', text: 'Only CSV files are supported' }]);
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

    const badge1 = BADGES[badgeIndex];
    const badge2 = BADGES[(badgeIndex + 1) % BADGES.length];
    const badge3 = BADGES[(badgeIndex + 2) % BADGES.length];

    return (
        <div className="chat-layout">
            <div className="session-sidebar">
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
            </div>
            <div className="chat-container">
                <div className="chat-messages">
                    {messages.length === 0 && homeSiteChecked && (
                        <div className="empty-state">
                            <div className="empty-state-logo-wrap">
                                <img src={logo} alt="Milestone Technologies" className="empty-state-logo" />
                            </div>
                            <div className="empty-state-brand">MileCore</div>
                            <div className="empty-state-sub">It simply works.</div>
                            <div className="capability-badges-row" key={badgeIndex}>
                                <span className="capability-badge" style={{ borderColor: badge1.color }}>{badge1.text}</span>
                                <span className="capability-badge" style={{ borderColor: badge2.color }}>{badge2.text}</span>
                                <span className="capability-badge" style={{ borderColor: badge3.color }}>{badge3.text}</span>
                            </div>
                        </div>
                    )}
                    {messages.map((m, i) => {
                        if (m.role === 'user') {
                            return (
                                <div key={i} className="message-row message-row-user">
                                    <ChatMessage role={m.role} text={m.text} sql={m.sql} file={m.file} timestamp={m.timestamp} />
                                    <img src={profilePics[pics.user]} alt="You" className="profile-pic" />
                                </div>
                            );
                        }
                        if (m.role === 'assistant') {
                            return (
                                <div key={i} className="message-row message-row-assistant">
                                    <img src={profilePics[pics.ai]} alt="AI" className="profile-pic" />
                                    <ChatMessage role={m.role} text={m.text} sql={m.sql} timestamp={m.timestamp} />
                                </div>
                            );
                        }
                        return <ChatMessage key={i} role={m.role} text={m.text} sql={m.sql} />;
                    })}
                    {loading && (
                        <div className="message-row message-row-assistant">
                            <img src={profilePics[pics.ai]} alt="AI" className="profile-pic" />
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
                                title="Upload CSV"
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                                </svg>
                            </button>
                            <input
                                ref={fileRef}
                                type="file"
                                accept=".csv"
                                style={{ display: 'none' }}
                                onChange={(e) => { stageFile(e.target.files[0]); e.target.value = ''; }}
                            />
                            {pendingFile && (
                                <div className="file-chip">
                                    <span className="file-chip-name">{pendingFile.name}</span>
                                    <button className="file-chip-dismiss" onClick={() => setPendingFile(null)}>&times;</button>
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
        </div>
    );
}
