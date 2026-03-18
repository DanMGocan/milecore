import { useState, useEffect, useRef, useCallback } from 'react';
import { Modal } from './components';

const PERSONAL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com',
    'protonmail.com', 'proton.me', 'aol.com', 'mail.com', 'zoho.com',
    'yandex.com', 'gmx.com', 'live.com'
];

/* --- SVG Icons for feature slides --- */
function ChatIcon() {
    return (
        <svg className="landing-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
    );
}
function PeopleIcon() {
    return (
        <svg className="landing-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
    );
}
function TicketIcon() {
    return (
        <svg className="landing-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><line x1="10" y1="9" x2="8" y2="9" />
        </svg>
    );
}
function UploadIcon() {
    return (
        <svg className="landing-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
        </svg>
    );
}
function MailIcon() {
    return (
        <svg className="landing-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
            <polyline points="22,6 12,13 2,6" />
        </svg>
    );
}
function ChartIcon() {
    return (
        <svg className="landing-feature-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
        </svg>
    );
}

/* --- Value card icons --- */
function MinimalIcon() {
    return (
        <svg className="landing-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" /><line x1="8" y1="12" x2="16" y2="12" />
        </svg>
    );
}
function BoltIcon() {
    return (
        <svg className="landing-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
    );
}
function TargetIcon() {
    return (
        <svg className="landing-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" />
        </svg>
    );
}

const FEATURES = [
    {
        title: 'Natural Language Chat',
        description: 'Ask questions about your data in plain English.',
        left: '"How many Dell laptops are out of warranty?"',
        right: 'AI returns a structured answer with counts and details.',
        Icon: ChatIcon,
    },
    {
        title: 'Asset & People Management',
        description: 'Add and update records just by talking.',
        left: '"Add Martha as AV Technician for Paris Office"',
        right: 'Database updated — new person record created and linked.',
        Icon: PeopleIcon,
    },
    {
        title: 'Support Request Tracking',
        description: 'Report issues and let AI handle the logging.',
        left: '"The printer on Floor 3 is jammed again"',
        right: 'Ticket created, linked to asset, priority assigned.',
        Icon: TicketIcon,
    },
    {
        title: 'CSV Bulk Import',
        description: 'Upload spreadsheets and let AI do the mapping.',
        left: 'User attaches CSV with 200 records',
        right: 'AI maps columns and imports all rows automatically.',
        Icon: UploadIcon,
    },
    {
        title: 'Email Integration',
        description: 'Draft and send emails through conversation.',
        left: '"Email HP asking if they can come on-site Tuesday"',
        right: 'Email drafted, reviewed, and sent — all from chat.',
        Icon: MailIcon,
    },
    {
        title: 'Dashboard & Reports',
        description: 'Visual summaries and automated reporting.',
        left: 'Dashboard charts overview of all assets and requests',
        right: 'Automated daily report email sent to stakeholders.',
        Icon: ChartIcon,
    }
];

/* --- Intersection observer for scroll-triggered animations --- */
function useReveal() {
    const ref = useRef(null);
    const [visible, setVisible] = useState(false);
    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } }, { threshold: 0.15 });
        obs.observe(el);
        return () => obs.disconnect();
    }, []);
    return [ref, visible];
}

export function LandingPage({ onNavigate }) {
    const [headerSolid, setHeaderSolid] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const [currentSlide, setCurrentSlide] = useState(0);
    const [demoModal, setDemoModal] = useState(false);
    const [formData, setFormData] = useState({ name: '', email: '', title: '', team: '' });
    const [formError, setFormError] = useState('');
    const [formSuccess, setFormSuccess] = useState(false);
    const [paused, setPaused] = useState(false);
    const touchStart = useRef(null);

    const [featRef, featVis] = useReveal();
    const [valRef, valVis] = useReveal();
    const [ctaRef, ctaVis] = useReveal();

    useEffect(() => {
        const onScroll = () => setHeaderSolid(window.scrollY > 50);
        window.addEventListener('scroll', onScroll, { passive: true });
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    useEffect(() => {
        const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (paused || prefersReduced) return;
        const id = setInterval(() => {
            setCurrentSlide(s => (s + 1) % FEATURES.length);
        }, 5000);
        return () => clearInterval(id);
    }, [paused]);

    const goToSlide = useCallback((i) => { setCurrentSlide(i); setPaused(true); }, []);
    const prevSlide = useCallback(() => { setCurrentSlide(s => (s - 1 + FEATURES.length) % FEATURES.length); setPaused(true); }, []);
    const nextSlide = useCallback(() => { setCurrentSlide(s => (s + 1) % FEATURES.length); setPaused(true); }, []);

    const handleTouchStart = (e) => { touchStart.current = e.touches[0].clientX; };
    const handleTouchEnd = (e) => {
        if (touchStart.current === null) return;
        const diff = touchStart.current - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) { diff > 0 ? nextSlide() : prevSlide(); }
        touchStart.current = null;
    };

    const scrollTo = (id) => { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }); setMenuOpen(false); };

    const handleSubmit = (e) => {
        e.preventDefault();
        setFormError('');
        if (!formData.name || !formData.email || !formData.title || !formData.team) { setFormError('All fields are required.'); return; }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) { setFormError('Please enter a valid email address.'); return; }
        const domain = formData.email.split('@')[1]?.toLowerCase();
        if (PERSONAL_DOMAINS.includes(domain)) { setFormError('Please use your company email.'); return; }
        setFormSuccess(true);
    };

    const resetForm = () => { setFormData({ name: '', email: '', title: '', team: '' }); setFormError(''); setFormSuccess(false); setDemoModal(false); };

    const SlideIcon = FEATURES[currentSlide].Icon;

    return (
        <div className="landing-page">
            {/* Animated background grid */}
            <div className="landing-grid-bg" aria-hidden="true" />

            <header className={`landing-header${headerSolid ? ' solid' : ''}`}>
                <div className="landing-header-inner">
                    <span className="landing-logo-text">TrueCore.cloud</span>
                    <button className="landing-hamburger" onClick={() => setMenuOpen(o => !o)} aria-label="Menu" aria-expanded={menuOpen}>
                        <span /><span /><span />
                    </button>
                    <nav className={`landing-nav${menuOpen ? ' open' : ''}`}>
                        <button onClick={() => scrollTo('features')}>Features</button>
                        <button onClick={() => scrollTo('about')}>About</button>
                        <button onClick={() => { onNavigate('chat'); setMenuOpen(false); }}>Go to App</button>
                        <button className="landing-cta-sm" onClick={() => { setDemoModal(true); setMenuOpen(false); }}>Request a Demo</button>
                    </nav>
                </div>
            </header>

            <section className="landing-hero">
                <div className="landing-hero-glow" aria-hidden="true" />
                <span className="landing-hero-badge">AI-Powered Site Operations</span>
                <h1>AI but with <span className="landing-gradient-text">no fluff.</span></h1>
                <p>It's simple, that's why it simply works.</p>
                <div className="landing-hero-actions">
                    <button className="landing-cta" onClick={() => setDemoModal(true)}>Request a Demo</button>
                    <button className="landing-cta-outline" onClick={() => onNavigate('chat')}>Try the App</button>
                </div>
                <div className="landing-scroll-indicator" aria-hidden="true"><span /><span /></div>
            </section>

            <section className={`landing-features${featVis ? ' visible' : ''}`} id="features" ref={featRef}>
                <span className="landing-section-label">Capabilities</span>
                <h2>What TrueCore.cloud Does</h2>

                <div className="landing-carousel-wrapper">
                    <div className="landing-carousel-icon-display" aria-hidden="true">
                        <SlideIcon />
                    </div>
                    <div className="landing-carousel" onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd}>
                        <div className="landing-carousel-track" style={{ transform: `translateX(-${currentSlide * 100}%)` }}>
                            {FEATURES.map((f, i) => (
                                <div className="landing-slide" key={i}>
                                    <h3>{f.title}</h3>
                                    <p className="landing-slide-desc">{f.description}</p>
                                    <div className="landing-slide-cols">
                                        <div className="landing-placeholder">
                                            <span className="landing-placeholder-label">User says...</span>
                                            <span className="landing-placeholder-text">{f.left}</span>
                                        </div>
                                        <div className="landing-placeholder landing-placeholder-result">
                                            <span className="landing-placeholder-label">Result...</span>
                                            <span className="landing-placeholder-text">{f.right}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                        <button className="landing-arrow landing-arrow-left" onClick={prevSlide} aria-label="Previous slide">&lsaquo;</button>
                        <button className="landing-arrow landing-arrow-right" onClick={nextSlide} aria-label="Next slide">&rsaquo;</button>
                    </div>
                </div>

                <div className="landing-dots" role="tablist" aria-label="Feature slides">
                    {FEATURES.map((_, i) => (
                        <button
                            key={i}
                            role="tab"
                            className={`landing-dot${i === currentSlide ? ' active' : ''}`}
                            onClick={() => goToSlide(i)}
                            aria-label={`Slide ${i + 1}: ${FEATURES[i].title}`}
                            aria-selected={i === currentSlide}
                        ></button>
                    ))}
                </div>

                {/* Feature mini-nav chips */}
                <div className="landing-feature-chips">
                    {FEATURES.map((f, i) => (
                        <button
                            key={i}
                            className={`landing-chip${i === currentSlide ? ' active' : ''}`}
                            onClick={() => goToSlide(i)}
                        >
                            <f.Icon />{f.title}
                        </button>
                    ))}
                </div>
            </section>

            <section className={`landing-value${valVis ? ' visible' : ''}`} id="about" ref={valRef}>
                <span className="landing-section-label">Why TrueCore.cloud</span>
                <h2>Built for the teams that keep things running.</h2>
                <p className="landing-value-sub">Small IT support and Facilities teams deserve real AI power — without the overengineering, bloated dashboards, or enterprise complexity.</p>
                <div className="landing-value-cards">
                    <div className="landing-card">
                        <MinimalIcon />
                        <h3>Not overengineered</h3>
                        <p>No dashboards you'll never use. No integrations you didn't ask for.</p>
                    </div>
                    <div className="landing-card">
                        <BoltIcon />
                        <h3>Real AI, real results</h3>
                        <p>Natural language that actually works. Ask, and it does.</p>
                    </div>
                    <div className="landing-card">
                        <TargetIcon />
                        <h3>Purpose-built</h3>
                        <p>Designed for IT support, facilities, and workplace tech teams.</p>
                    </div>
                </div>
            </section>

            <section className={`landing-final-cta${ctaVis ? ' visible' : ''}`} ref={ctaRef}>
                <div className="landing-final-cta-glow" aria-hidden="true" />
                <h2>Ready to see it in action?</h2>
                <p>Get a personalized walkthrough of TrueCore.cloud for your team.</p>
                <button className="landing-cta" onClick={() => setDemoModal(true)}>Request a Demo</button>
            </section>

            <footer className="landing-footer">
                <p>&copy; {new Date().getFullYear()} TrueCore.cloud. All rights reserved.</p>
            </footer>

            <Modal open={demoModal} onClose={resetForm} title="Request a Demo" className="landing-modal">
                {formSuccess ? (
                    <div className="landing-form-success">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
                        </svg>
                        <p>Thank you, we'll be in touch.</p>
                        <div className="modal-actions">
                            <button className="btn landing-btn-primary" onClick={resetForm}>Close</button>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} noValidate>
                        <div className="form-group">
                            <label htmlFor="demo-name">Name</label>
                            <input id="demo-name" className="form-input landing-input" type="text" required value={formData.name} onChange={e => setFormData(d => ({ ...d, name: e.target.value }))} />
                        </div>
                        <div className="form-group">
                            <label htmlFor="demo-email">Email</label>
                            <input id="demo-email" className="form-input landing-input" type="email" required value={formData.email} onChange={e => setFormData(d => ({ ...d, email: e.target.value }))} />
                        </div>
                        <div className="form-group">
                            <label htmlFor="demo-title">Title</label>
                            <input id="demo-title" className="form-input landing-input" type="text" required value={formData.title} onChange={e => setFormData(d => ({ ...d, title: e.target.value }))} />
                        </div>
                        <div className="form-group">
                            <label htmlFor="demo-team">Team</label>
                            <input id="demo-team" className="form-input landing-input" type="text" required value={formData.team} onChange={e => setFormData(d => ({ ...d, team: e.target.value }))} />
                        </div>
                        {formError && <p className="landing-form-error" role="alert">{formError}</p>}
                        <div className="modal-actions">
                            <button type="button" className="btn landing-btn" onClick={resetForm}>Cancel</button>
                            <button type="submit" className="btn landing-btn-primary">Submit</button>
                        </div>
                    </form>
                )}
            </Modal>
        </div>
    );
}
