import { useState, useEffect, useRef } from 'react';

const TOC = [
    { id: 'overview', label: 'Overview' },
    { id: 'features', label: 'Features' },
    { id: 'chat', label: 'Chat Interface' },
    { id: 'capabilities', label: 'What You Can Do' },
    { id: 'csv-import', label: 'CSV Import' },
    { id: 'approvals', label: 'Approval System' },
    { id: 'database-browser', label: 'Database Browser' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'email', label: 'Email' },
    { id: 'user-roles', label: 'User Roles' },
    { id: 'daily-reports', label: 'Daily Reports' },
    { id: 'important-flags', label: 'Important Flags' },
    { id: 'projects', label: 'Projects' },
    { id: 'knowledge', label: 'Knowledge Management' },
    { id: 'schema', label: 'Database Schema' },
    { id: 'scope', label: 'Scope & Limitations' },
    { id: 'qa-testing', label: 'QA & Testing' },
    { id: 'roadmap', label: 'Roadmap' },
    { id: 'cost-estimate', label: 'Cost Estimate' },
];

export function DocumentationPage() {
    const [activeId, setActiveId] = useState('overview');
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const contentRef = useRef(null);

    useEffect(() => {
        const container = contentRef.current;
        if (!container) return;
        const sections = container.querySelectorAll('section[id]');
        const observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        setActiveId(entry.target.id);
                        break;
                    }
                }
            },
            { root: container, rootMargin: '-10% 0px -80% 0px', threshold: 0 }
        );
        sections.forEach(s => observer.observe(s));
        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        const hash = window.location.hash.slice(1);
        if (hash) {
            const el = document.getElementById(hash);
            if (el) el.scrollIntoView({ behavior: 'smooth' });
        }
    }, []);

    const scrollTo = (id) => {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: 'smooth' });
        setSidebarOpen(false);
    };

    return (
        <div className="doc-layout">
            <div className={`sidebar-backdrop${sidebarOpen ? ' visible' : ''}`} onClick={() => setSidebarOpen(false)} />
            <button className="doc-sidebar-toggle sidebar-toggle-btn" onClick={() => setSidebarOpen(o => !o)} aria-label="Toggle contents">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/>
                </svg>
            </button>
            <nav className={`doc-sidebar${sidebarOpen ? ' open' : ''}`}>
                <div className="doc-toc-title">Contents</div>
                {TOC.map(t => (
                    <button
                        key={t.id}
                        className={`doc-toc-item${activeId === t.id ? ' active' : ''}`}
                        onClick={() => scrollTo(t.id)}
                    >
                        {t.label}
                    </button>
                ))}
            </nav>
            <div className="doc-content" ref={contentRef}>
                <OverviewSection />
                <FeaturesSection />
                <ChatSection />
                <CapabilitiesSection />
                <CsvImportSection />
                <ApprovalsSection />
                <DatabaseBrowserSection />
                <DashboardSection />
                <EmailSection />
                <UserRolesSection />
                <DailyReportsSection />
                <ImportantFlagsSection />
                <ProjectsSection />
                <KnowledgeSection />
                <SchemaSection />
                <ScopeSection />
                <QATestingSection />
                <RoadmapSection />
                <CostEstimateSection />
            </div>
        </div>
    );
}

function OverviewSection() {
    return (
        <section id="overview" className="doc-section">
            <h2>Overview</h2>
            <p>
                TrueCore.cloud is an AI-powered database assistant built for technical site operations. It helps IT support teams, tech bar technicians, AV support, and workplace technology teams store and retrieve operational data through natural language conversation.
            </p>
            <h3>Tech Stack</h3>
            <ul>
                <li><strong>Backend:</strong> Python with FastAPI, PostgreSQL database</li>
                <li><strong>AI:</strong> Anthropic Claude via streaming API</li>
                <li><strong>Frontend:</strong> React (Vite), Recharts for dashboard visualizations</li>
                <li><strong>Email:</strong> Brevo SMTP relay</li>
            </ul>
            <h3>Getting Started</h3>
            <p>
                TrueCore.cloud boots with a seeded default <strong>home site</strong>: <strong>Dublin HQ</strong>. All operations default to that site unless you explicitly specify another one.
            </p>
            <div className="doc-callout">
                <strong>Bootstrap seed:</strong> The initial company, home site, and default users are restored automatically on first launch and after a database reset.
            </div>
            <h3>Core Workflow</h3>
            <p>TrueCore.cloud is organized around the lifecycle of site operations:</p>
            <ol className="doc-flow">
                <li className="doc-flow-step">Person reports a problem</li>
                <li className="doc-flow-step">Support request created</li>
                <li className="doc-flow-step">Asset identified and linked</li>
                <li className="doc-flow-step">Technical issue diagnosed</li>
                <li className="doc-flow-step">Work performed and logged</li>
                <li className="doc-flow-step">Resolution recorded</li>
                <li className="doc-flow-step">Knowledge captured for future reference</li>
            </ol>
        </section>
    );
}

function FeaturesSection() {
    return (
        <section id="features" className="doc-section">
            <h2>Features</h2>
            <p>A complete list of everything TrueCore.cloud can do, organized by area.</p>

            <h3>AI Chat</h3>
            <ul>
                <li>Natural language conversation — ask questions and give instructions in plain English</li>
                <li>Real-time streaming responses via Server-Sent Events</li>
                <li>Multi-step operations — the AI coordinates across multiple tables in one request</li>
                <li>Context-aware — understands the current user, home site, and relative dates</li>
                <li>Markdown-rendered responses with formatted tables, lists, and code blocks</li>
                <li>Collapsible SQL operation blocks showing what was executed and the result</li>
                <li>Conversation history with session sidebar — resume any previous chat</li>
                <li>Suggested example prompts on empty chat to help new users get started</li>
            </ul>

            <h3>Data Management</h3>
            <ul>
                <li>People and teams — add, update, and query staff, clients, vendors, and supervisors</li>
                <li>Assets and equipment — register, track lifecycle status, link parent/child relationships</li>
                <li>Support requests — create, prioritize, update status, and resolve</li>
                <li>Technical issues — log issues, record recurring occurrences, track severity</li>
                <li>Events and scheduling — meetings, vendor visits, outages, maintenance windows</li>
                <li>Event participants and equipment reservations</li>
                <li>Inventory management — stock items, restock, check out, transfer between sites</li>
                <li>Work logs — time tracking tied to requests, issues, or assets</li>
                <li>Notes — freeform notes attached to any entity, including handover and follow-up notes</li>
                <li>PTO and leave tracking for staff</li>
                <li>Change management — log infrastructure changes with risk level and scheduling</li>
                <li>Projects — track multi-step initiatives with tasks, budgets, expenses, and team members</li>
                <li>Vendor contracts — track vendors, SLAs, and contract expiry dates</li>
                <li>Sites and rooms — manage locations and physical spaces</li>
                <li>Tagging — flexible tagging system across all entity types</li>
                <li>Audit log — automatic tracking of all data changes</li>
            </ul>

            <h3>Knowledge Management</h3>
            <ul>
                <li>Knowledge articles — troubleshooting guides, SOPs, reference documents</li>
                <li>Workflows — document operational processes step by step</li>
                <li>Miscellaneous knowledge — store operational info like office hours, policies, and procedures</li>
            </ul>

            <h3>CSV Bulk Import</h3>
            <ul>
                <li>Upload CSV files through chat via the paperclip button</li>
                <li>AI-powered column mapping — the AI analyzes headers and proposes a mapping to the target table</li>
                <li>Confirmation step before executing — review and adjust mappings</li>
                <li>Dry-run validation with SAVEPOINT before committing</li>
                <li>Duplicate handling with INSERT OR IGNORE</li>
                <li>Approval integration — imports can be routed for admin review</li>
            </ul>

            <h3>Email Integration</h3>
            <ul>
                <li>Send emails through chat — describe who and what, the AI drafts and sends</li>
                <li>Recipient lookup — the AI verifies email addresses from the database before sending</li>
                <li>Automated daily reports — scheduled email summaries sent to supervisors</li>
                <li>Manual daily report trigger from the dashboard (admin only)</li>
            </ul>

            <h3>Excel File Generation</h3>
            <ul>
                <li>Generate downloadable Excel files from any query through chat</li>
                <li>Export the entire database to a single .xlsx file with one sheet per table</li>
                <li>Export the entire database to a downloadable Excel file</li>
            </ul>

            <h3>Approval System</h3>
            <ul>
                <li>Admin-defined approval rules that intercept write operations (INSERT, UPDATE, DELETE)</li>
                <li>Queued pending approvals with full SQL and explanation visible to reviewers</li>
                <li>Approve or reject through chat with optional notes</li>
                <li>Pending approval badge count on the Chat nav link for admins</li>
                <li>CSV imports that match rules are also queued for review</li>
            </ul>

            <h3>Database Browser</h3>
            <ul>
                <li>Visual table browser with row counts per table</li>
                <li>Schema viewer — column names, types, primary key and NOT NULL indicators</li>
                <li>Paginated data grid (50 rows per page)</li>
                <li>Insert rows via form</li>
                <li>Delete individual rows</li>
                <li>Create new tables with custom column definitions</li>
                <li>Add columns to existing tables</li>
            </ul>

            <h3>Dashboard</h3>
            <ul>
                <li>Stat cards — active assets, open tickets, open issues, events this week, important items</li>
                <li>Charts — assets over time, issues by severity, tickets by status, staff per site, vendor visits</li>
                <li>Database management — export to Excel, import &amp; merge from .xlsx</li>
                <li>Admin actions — send daily report, reset database</li>
            </ul>

            <h3>User System</h3>
            <ul>
                <li>Two roles: admin and standard user</li>
                <li>User switching — toggle between users to test different permission levels</li>
                <li>Per-user conversation history</li>
                <li>Admin-only tools — approval management, daily reports, database reset</li>
                <li>User profile display with name, title, role, and admin badge</li>
            </ul>

            <h3>Important Flags</h3>
            <ul>
                <li>Flag any record as important across all major tables</li>
                <li>Dashboard stat card counts all flagged items</li>
                <li>Daily report highlights important items</li>
            </ul>

            <h3>Mobile &amp; Responsive</h3>
            <ul>
                <li>Fully responsive layout across all pages</li>
                <li>Hamburger menu navigation on mobile</li>
                <li>Off-canvas sidebars for chat, database browser, and documentation</li>
                <li>Touch-friendly targets (44px minimum)</li>
                <li>Landing page carousel with touch swipe support</li>
            </ul>
        </section>
    );
}

function ChatSection() {
    return (
        <section id="chat" className="doc-section">
            <h2>Chat Interface</h2>
            <p>
                The chat page is the primary way to interact with TrueCore.cloud. Type natural language messages and the AI will translate your intent into database operations.
            </p>
            <h3>Sending Messages</h3>
            <p>
                Type in the input box at the bottom and press <span className="doc-code">Enter</span> to send. Use <span className="doc-code">Shift+Enter</span> for a new line without sending. You can also attach CSV files using the paperclip button.
            </p>
            <h3>Streaming Responses</h3>
            <p>
                Responses stream in real-time via Server-Sent Events. You'll see a typing indicator while the AI processes your request, then text appears token by token.
            </p>
            <h3>Conversation Sidebar</h3>
            <p>
                The left sidebar shows your conversation history. Click any session to resume it. Use the <strong>+ New</strong> button to start a fresh conversation. Sessions are stored per user and titled automatically from your first message.
            </p>
            <h3>SQL Operation Blocks</h3>
            <p>
                When the AI executes database queries, a collapsible block appears below the response showing the SQL executed, an explanation of what it did, and the result (row count or error). Click the block to expand it.
            </p>
            <h3>Markdown Rendering</h3>
            <p>
                Assistant responses render Markdown: bold, italic, lists, inline code, code blocks, and more. Tables in responses are also formatted.
            </p>
        </section>
    );
}

function CapabilitiesSection() {
    return (
        <section id="capabilities" className="doc-section">
            <h2>What You Can Do</h2>
            <p>
                TrueCore.cloud understands natural language requests across many operational domains. Here's what you can ask, organized by category.
            </p>

            <h3>People & Teams</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Add a new technician</td><td>"Add John Smith as a new tech, he works for Milestone"</td></tr>
                    <tr><td>Register a client contact</td><td>"Sarah Lee is a new contact at the client site, her email is sarah@client.com"</td></tr>
                    <tr><td>Create a team</td><td>"Create an AV support team with John and Sarah"</td></tr>
                    <tr><td>Log PTO / sick leave</td><td>"John is out on PTO from March 10 to March 14"</td></tr>
                    <tr><td>Look up contact info</td><td>"What's Sarah's email?" or "Who's on the AV team?"</td></tr>
                </tbody>
            </table>

            <h3>Assets & Equipment</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Register an asset</td><td>"Add a new Dell laptop, serial ABC123, assigned to John"</td></tr>
                    <tr><td>Update asset status</td><td>"Mark laptop ABC123 as in repair"</td></tr>
                    <tr><td>Link assets together</td><td>"The docking station is connected to John's laptop"</td></tr>
                    <tr><td>Search assets</td><td>"Show all spare monitors" or "What's assigned to Sarah?"</td></tr>
                    <tr><td>Decommission</td><td>"Decommission the old printer on floor 3"</td></tr>
                </tbody>
            </table>

            <h3>Issues & Support Requests</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Create a request</td><td>"John walked in about a broken monitor, high priority"</td></tr>
                    <tr><td>Log an issue</td><td>"There's a recurring Wi-Fi issue in Building A, Room 201"</td></tr>
                    <tr><td>Update status</td><td>"Mark request #5 as resolved"</td></tr>
                    <tr><td>Record occurrence</td><td>"The Wi-Fi issue happened again today in Room 201"</td></tr>
                    <tr><td>Query open items</td><td>"Show all open critical requests" or "What issues are recurring?"</td></tr>
                </tbody>
            </table>

            <h3>Events & Scheduling</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Create an event</td><td>"Schedule a meeting in Room A tomorrow at 2pm"</td></tr>
                    <tr><td>Vendor visit</td><td>"Cisco is visiting next Monday for a network audit"</td></tr>
                    <tr><td>Log an outage</td><td>"There was an internet outage from 9am to 11am today"</td></tr>
                    <tr><td>Attach participants</td><td>"Add John and Sarah to the Monday meeting"</td></tr>
                    <tr><td>Reserve equipment</td><td>"We need 2 projectors for the all-hands meeting"</td></tr>
                </tbody>
            </table>

            <h3>Inventory & Spare Parts</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Add inventory item</td><td>"Add HDMI cables as a consumable item"</td></tr>
                    <tr><td>Restock</td><td>"Restock 50 HDMI cables at the Dublin site"</td></tr>
                    <tr><td>Check out</td><td>"Check out 2 HDMI cables for the boardroom setup"</td></tr>
                    <tr><td>Check stock levels</td><td>"How many USB-C adapters do we have?"</td></tr>
                    <tr><td>Transfer</td><td>"Transfer 10 cables from Dublin to London"</td></tr>
                </tbody>
            </table>

            <h3>Work Logs & Notes</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Log work</td><td>"I spent 30 minutes troubleshooting John's laptop"</td></tr>
                    <tr><td>Add a note</td><td>"Add a handover note: printer on floor 2 needs toner"</td></tr>
                    <tr><td>Follow-up</td><td>"Add a follow-up note on request #3"</td></tr>
                    <tr><td>View work history</td><td>"Show all work logs from this week"</td></tr>
                </tbody>
            </table>

            <h3>Email</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Send an email</td><td>"Email John about the scheduled maintenance tomorrow"</td></tr>
                    <tr><td>Notify a group</td><td>"Send the AV team an email about the new projector setup"</td></tr>
                </tbody>
            </table>

            <h3>Projects & Budget</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Create a project</td><td>"Create a project called Network Refresh for Dublin HQ with a €10,000 budget"</td></tr>
                    <tr><td>Add team members</td><td>"Add Sarah as project manager on the Network Refresh"</td></tr>
                    <tr><td>Break into tasks</td><td>"Add tasks: order switches, run cabling, configure VLANs, test connectivity"</td></tr>
                    <tr><td>Create sub-tasks</td><td>"Add a sub-task under 'run cabling' for floor 2 wiring"</td></tr>
                    <tr><td>Log expenses</td><td>"Log an expense of €3,200 for Cisco switches, category hardware"</td></tr>
                    <tr><td>Check budget</td><td>"What's the budget status on the Network Refresh project?"</td></tr>
                    <tr><td>Post updates</td><td>"Post an update on Network Refresh: cabling complete on floors 1 and 2"</td></tr>
                    <tr><td>Link entities</td><td>"Link the Cisco contract to the Network Refresh project"</td></tr>
                    <tr><td>Query projects</td><td>"Show all active projects" or "What projects is Sarah working on?"</td></tr>
                </tbody>
            </table>

            <h3>Knowledge & Vendors</h3>
            <table className="doc-table">
                <thead><tr><th>Action</th><th>Example Phrase</th></tr></thead>
                <tbody>
                    <tr><td>Create an article</td><td>"Write a troubleshooting guide for the conference room AV setup"</td></tr>
                    <tr><td>Add operational info</td><td>"The office is closed December 25 to January 1"</td></tr>
                    <tr><td>Log a workflow</td><td>"Document the new laptop provisioning process"</td></tr>
                    <tr><td>Manage vendors</td><td>"Add Cisco as a hardware vendor, contract expires Dec 2025"</td></tr>
                    <tr><td>Track changes</td><td>"Log a network switch upgrade, medium risk, scheduled for Friday"</td></tr>
                </tbody>
            </table>
        </section>
    );
}

function CsvImportSection() {
    return (
        <section id="csv-import" className="doc-section">
            <h2>CSV Import</h2>
            <p>
                TrueCore.cloud supports bulk data import via CSV files. The AI analyzes your file, maps columns to the target table, and imports the data.
            </p>
            <h3>Import Flow</h3>
            <ol className="doc-flow">
                <li className="doc-flow-step"><strong>Upload:</strong> Click the paperclip button in the chat input and select a <span className="doc-code">.csv</span> file. Only CSV format is supported.</li>
                <li className="doc-flow-step"><strong>Staging:</strong> The file is uploaded to the server. The AI receives the filename, column headers, total row count, and a sample of the data.</li>
                <li className="doc-flow-step"><strong>AI Mapping:</strong> The AI analyzes the CSV columns and proposes a mapping to the target database table. It identifies which CSV columns correspond to which table columns.</li>
                <li className="doc-flow-step"><strong>Confirmation:</strong> The AI presents the proposed mapping and asks you to confirm. You can request changes before proceeding.</li>
                <li className="doc-flow-step"><strong>Execution:</strong> On confirmation, the AI calls the import tool. The system validates the data with a SAVEPOINT (dry run), then commits. Auto-generated columns like <span className="doc-code">id</span>, <span className="doc-code">created_at</span>, and <span className="doc-code">updated_at</span> are skipped.</li>
            </ol>

            <div className="doc-callout doc-callout--tip">
                <strong>Tip:</strong> You can add a note when uploading, like "import these as hardware assets" to help the AI pick the right target table.
            </div>

            <h3>Approval Integration</h3>
            <p>
                If approval rules are active, CSV imports that match a rule are queued for admin review instead of executing immediately. See the <strong>Approval System</strong> section below.
            </p>
        </section>
    );
}

function ApprovalsSection() {
    return (
        <section id="approvals" className="doc-section">
            <h2>Approval System</h2>
            <p>
                Admins can create approval rules that intercept write operations (INSERT, UPDATE, DELETE) before they execute. This adds a review layer for sensitive changes.
            </p>

            <h3>Creating Rules</h3>
            <p>
                Only admin users can manage approval rules. Ask TrueCore.cloud to create a rule by describing what should require approval:
            </p>
            <div className="doc-code-block">
                "Add an approval rule: any changes to the assets table need approval"<br />
                "Create a rule requiring approval for all DELETE operations"
            </div>
            <p>
                Rules are stored with a description and can be activated or deactivated. The AI matches incoming write operations against active rules by description.
            </p>

            <h3>How Writes Get Intercepted</h3>
            <ol>
                <li>A write operation is requested (via chat or CSV import)</li>
                <li>The system checks if the operation matches any active approval rule</li>
                <li>If matched: the SQL and explanation are queued in <span className="doc-code">pending_approvals</span> with status "pending"</li>
                <li>If not matched: the operation executes normally</li>
            </ol>

            <h3>Reviewing Approvals</h3>
            <p>Admins can review pending approvals through chat:</p>
            <div className="doc-code-block">
                "Show pending approvals"<br />
                "Approve approval #3"<br />
                "Reject approval #3 with note: not authorized"
            </div>
            <p>
                Approved operations execute immediately. Rejected operations are marked as rejected and never run. The pending approval count appears as a badge on the Chat nav link for admin users.
            </p>

            <h3>CSV Import Approval</h3>
            <p>
                When a CSV import matches an active approval rule, the entire import is queued. The admin can review the SQL statements and approve or reject the batch.
            </p>
        </section>
    );
}

function DatabaseBrowserSection() {
    return (
        <section id="database-browser" className="doc-section">
            <h2>Database Browser</h2>
            <p>
                The Database page provides a visual interface for browsing, editing, and managing all tables in the TrueCore.cloud database.
            </p>

            <h3>Table List</h3>
            <p>
                The left sidebar lists all database tables with their row counts. Click a table to view its contents in the main area.
            </p>

            <h3>Schema View</h3>
            <p>
                When you select a table, a schema bar at the top shows all columns with their names, data types, primary key markers, and NOT NULL constraints.
            </p>

            <h3>Data Grid</h3>
            <p>
                Table data is displayed in a paginated grid. Rows are shown 50 at a time. Each row has a delete button that appears on hover.
            </p>

            <h3>CRUD Operations</h3>
            <ul>
                <li><strong>Create:</strong> Click "Add Row" to open a form with all columns. Fill in the values and submit.</li>
                <li><strong>Read:</strong> Browse the data grid, paginate through rows.</li>
                <li><strong>Update:</strong> Not available in the browser UI (use chat for updates).</li>
                <li><strong>Delete:</strong> Hover over a row and click the red delete button.</li>
            </ul>

            <h3>Pagination</h3>
            <p>
                Navigate pages with Previous/Next buttons. The current page and total are displayed between the buttons.
            </p>

            <h3>Create Table & Add Column</h3>
            <p>
                Use the toolbar buttons to create entirely new tables or add columns to existing tables. A modal form guides you through the process.
            </p>

            <h3>Export & Download</h3>
            <ul>
                <li><strong>Export Excel:</strong> Exports all tables to a downloadable <span className="doc-code">.xlsx</span> file</li>
                <li><strong>Export Excel:</strong> Exports all tables to a single <span className="doc-code">.xlsx</span> file with one sheet per table</li>
            </ul>
        </section>
    );
}

function DashboardSection() {
    return (
        <section id="dashboard" className="doc-section">
            <h2>Dashboard</h2>
            <p>
                The Dashboard provides a high-level overview of your site's operational data with stats, charts, and management tools.
            </p>

            <h3>Stat Cards</h3>
            <p>Five cards at the top show key metrics at a glance:</p>
            <ul>
                <li><strong>Active Assets</strong> &mdash; count of assets with lifecycle_status = 'active'</li>
                <li><strong>Open Tickets</strong> &mdash; tickets with status 'open' or 'in_progress'</li>
                <li><strong>Open Issues</strong> &mdash; technical issues not yet resolved</li>
                <li><strong>Events This Week</strong> &mdash; events scheduled in the current week</li>
                <li><strong>Important Items</strong> &mdash; total items flagged as important across all tables</li>
            </ul>

            <h3>Charts</h3>
            <p>Four visualization panels powered by Recharts:</p>
            <ul>
                <li><strong>Assets by Period</strong> &mdash; assets created per day over the last 30 days (area chart)</li>
                <li><strong>Issues Summary</strong> &mdash; tickets by status and issues by severity (bar charts)</li>
                <li><strong>Vendor Visits</strong> &mdash; vendor visit events grouped by status (bar chart)</li>
                <li><strong>Staff per Site</strong> &mdash; employee count at each site (bar chart)</li>
            </ul>

            <h3>Database Management</h3>
            <p>A management panel at the bottom provides:</p>
            <ul>
                <li><strong>Export to Excel</strong> &mdash; download all data as <span className="doc-code">.xlsx</span></li>
                <li><strong>Import Merge</strong> &mdash; upload an Excel file to merge data into existing tables</li>
            </ul>

            <h3>Admin Actions</h3>
            <p>Admin users see additional buttons:</p>
            <ul>
                <li><strong>Send Daily Report</strong> &mdash; manually triggers the daily report email to all supervisors</li>
                <li><strong>Reset Database</strong> &mdash; re-initializes the database and restores the default bootstrap seed (destroys all other data)</li>
            </ul>
            <div className="doc-callout doc-callout--warning">
                <strong>Warning:</strong> Reset Database is destructive and cannot be undone. It drops all data, recreates tables, and restores the default seeded company, site, and users.
            </div>
        </section>
    );
}

function EmailSection() {
    return (
        <section id="email" className="doc-section">
            <h2>Email</h2>
            <p>
                TrueCore.cloud can send emails on your behalf through the <span className="doc-code">send_email</span> tool. Emails are sent via Brevo (formerly Sendinblue) SMTP relay.
            </p>

            <h3>How It Works</h3>
            <ol>
                <li>Ask the AI to email someone: "Email John about the maintenance window tomorrow"</li>
                <li>The AI looks up the recipient's email address from the <span className="doc-code">people</span> table</li>
                <li>If found, it composes and sends a plain-text email</li>
                <li>The sent email appears in the SQL operations block as a logged action</li>
            </ol>

            <div className="doc-callout doc-callout--tip">
                <strong>Recipient lookup is required.</strong> The AI must find the recipient's email in the database before sending. If the person doesn't have an email address on file, the AI will tell you and ask you to add one.
            </div>

            <h3>Brevo SMTP Configuration</h3>
            <p>Email requires these environment variables to be set:</p>
            <table className="doc-table">
                <thead><tr><th>Variable</th><th>Description</th></tr></thead>
                <tbody>
                    <tr><td><span className="doc-code">BREVO_SMTP_HOST</span></td><td>SMTP server (default: smtp-relay.brevo.com)</td></tr>
                    <tr><td><span className="doc-code">BREVO_SMTP_PORT</span></td><td>SMTP port (default: 587, TLS)</td></tr>
                    <tr><td><span className="doc-code">BREVO_SMTP_LOGIN</span></td><td>SMTP login credential</td></tr>
                    <tr><td><span className="doc-code">BREVO_SMTP_PASSWORD</span></td><td>SMTP password</td></tr>
                    <tr><td><span className="doc-code">BREVO_SENDER_EMAIL</span></td><td>From address for outgoing mail</td></tr>
                    <tr><td><span className="doc-code">BREVO_SENDER_NAME</span></td><td>Display name for the sender</td></tr>
                </tbody>
            </table>

            <h3>API Key Configuration</h3>
            <p>TrueCore.cloud requires an Anthropic API key and optionally supports a spare key for automatic failover:</p>
            <table className="doc-table">
                <thead><tr><th>Variable</th><th>Description</th></tr></thead>
                <tbody>
                    <tr><td><span className="doc-code">ANTHROPIC_API_KEY</span></td><td>Primary API key (required)</td></tr>
                    <tr><td><span className="doc-code">ANTHROPIC_API_KEY_SPARE</span></td><td>Fallback API key (optional). Automatically used if the primary key hits a rate limit or authentication error</td></tr>
                </tbody>
            </table>
            <div className="doc-callout doc-callout--tip">
                <strong>Automatic failover:</strong> If a spare key is configured, TrueCore.cloud will seamlessly switch to it when the primary key is rate-limited or fails authentication. This happens transparently with no interruption to the user's conversation.
            </div>
        </section>
    );
}

function UserRolesSection() {
    return (
        <section id="user-roles" className="doc-section">
            <h2>User Roles</h2>
            <p>
                TrueCore.cloud has two user roles that control access to administrative features.
            </p>

            <h3>Admin</h3>
            <ul>
                <li>Can create, list, and remove approval rules</li>
                <li>Can review, approve, and reject pending approvals</li>
                <li>Sees the pending approval badge count on the Chat nav link</li>
                <li>Can trigger daily reports manually from the Dashboard</li>
                <li>Can reset the database from the Dashboard</li>
            </ul>

            <h3>User (Standard)</h3>
            <ul>
                <li>Full access to chat, database browser, and dashboard</li>
                <li>Can read and write data through the chat</li>
                <li>Cannot manage approval rules or review approvals</li>
                <li>Cannot trigger admin actions on the Dashboard</li>
            </ul>

            <h3>Role Configuration</h3>
            <p>
                User roles are stored in the <span className="doc-code">people</span> table. A person becomes an app user when <span className="doc-code">is_user = 1</span>, and their role is set via the <span className="doc-code">user_role</span> column (<span className="doc-code">'admin'</span> or <span className="doc-code">'user'</span>).
            </p>
        </section>
    );
}

function DailyReportsSection() {
    return (
        <section id="daily-reports" className="doc-section">
            <h2>Daily Reports</h2>
            <p>
                TrueCore.cloud automatically generates and sends daily site reports via email to designated supervisors.
            </p>

            <h3>Automatic Scheduling</h3>
            <p>
                Reports run automatically at a configured time (default: 7:00 AM) using a background loop. The schedule is controlled by environment variables:
            </p>
            <table className="doc-table">
                <thead><tr><th>Variable</th><th>Default</th><th>Description</th></tr></thead>
                <tbody>
                    <tr><td><span className="doc-code">DAILY_REPORT_HOUR</span></td><td>7</td><td>Hour to send report (24h format)</td></tr>
                    <tr><td><span className="doc-code">DAILY_REPORT_MINUTE</span></td><td>0</td><td>Minute to send report</td></tr>
                </tbody>
            </table>

            <h3>Supervisor Setup</h3>
            <p>
                To receive daily reports, a person must have <span className="doc-code">is_supervisor = 1</span> in the <span className="doc-code">people</span> table and have a valid email address. Reports are generated per site, so each supervisor receives the report for their associated site.
            </p>

            <h3>Report Contents</h3>
            <p>Each daily report includes three sections:</p>
            <ul>
                <li><strong>New Issues from Yesterday</strong> &mdash; technical issues created in the last 24 hours</li>
                <li><strong>Vendor Visits Scheduled for Today</strong> &mdash; vendor visit events happening today</li>
                <li><strong>Items Flagged as Important</strong> &mdash; anything marked important from yesterday</li>
            </ul>

            <h3>Manual Trigger</h3>
            <p>
                Admin users can manually send the daily report from the Dashboard using the "Send Daily Report" button, or by asking the AI: "Send the daily report now."
            </p>
        </section>
    );
}

function ImportantFlagsSection() {
    return (
        <section id="important-flags" className="doc-section">
            <h2>Important Flags</h2>
            <p>
                Many tables include an <span className="doc-code">important</span> column (integer, 0 or 1) that lets you flag records for special attention.
            </p>

            <h3>Tables with Important Flags</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '12px 0' }}>
                {['technical_issues', 'tickets', 'events', 'notes', 'changes', 'work_logs', 'assets', 'inventory_transactions', 'misc_knowledge', 'workflows', 'projects'].map(t => (
                    <span key={t} className="doc-badge">{t}</span>
                ))}
            </div>

            <h3>Flagging & Unflagging</h3>
            <p>Use natural language to manage flags:</p>
            <div className="doc-code-block">
                "Flag ticket #5 as important"<br />
                "Mark the Wi-Fi issue as important"<br />
                "Unflag asset #12"
            </div>

            <h3>Where Important Items Appear</h3>
            <ul>
                <li><strong>Dashboard:</strong> The "Important Items" stat card shows the total count across all tables</li>
                <li><strong>Daily Reports:</strong> Items flagged as important from the previous day are included in the supervisor email</li>
                <li><strong>Chat Queries:</strong> You can ask "Show all important items" or "What's flagged as important?"</li>
            </ul>
        </section>
    );
}

function ProjectsSection() {
    return (
        <section id="projects" className="doc-section">
            <h2>Projects</h2>
            <p>
                TrueCore.cloud includes a general-purpose project tracking system for managing multi-step initiatives like infrastructure rollouts, office moves, hardware refreshes, and process improvements — all through the chat interface.
            </p>

            <h3>Creating a Project</h3>
            <p>Tell the AI what you're working on and it creates the project with the right fields:</p>
            <div className="doc-code-block">
                "Create a project called Network Refresh for Dublin HQ with a €10,000 budget"<br />
                "Start a new deployment project for the AV upgrade, high priority, category infrastructure"
            </div>
            <p>Projects track:</p>
            <ul>
                <li><strong>Status:</strong> planned, active, on_hold, completed, cancelled</li>
                <li><strong>Priority:</strong> low, medium, high, critical</li>
                <li><strong>Category:</strong> infrastructure, operations, maintenance, deployment, migration, other</li>
                <li><strong>Timeline:</strong> planned start/end dates and actual start/end dates</li>
                <li><strong>Budget:</strong> estimated budget cap and currency (default EUR)</li>
                <li><strong>Owner:</strong> linked to a person in the system</li>
                <li><strong>Site:</strong> optionally linked to a specific site</li>
            </ul>

            <h3>Team Members</h3>
            <p>Assign people to projects with specific roles:</p>
            <div className="doc-code-block">
                "Add Sarah as project manager on the Network Refresh"<br />
                "Add John and Mike as contributors to the AV upgrade project"
            </div>
            <p>Roles: <span className="doc-code">manager</span>, <span className="doc-code">contributor</span>, <span className="doc-code">stakeholder</span>, <span className="doc-code">observer</span>. Each person can only be assigned once per project.</p>

            <h3>Tasks & Sub-Tasks</h3>
            <p>Break projects into actionable work items. Tasks can be nested for complex breakdowns:</p>
            <div className="doc-code-block">
                "Add tasks to Network Refresh: order switches, run cabling, configure VLANs, test connectivity"<br />
                "Add a sub-task under 'run cabling' for floor 2 wiring"<br />
                "Mark the 'order switches' task as done"<br />
                "What tasks are still open on the Network Refresh?"
            </div>
            <p>Tasks have their own status (<span className="doc-code">todo</span>, <span className="doc-code">in_progress</span>, <span className="doc-code">done</span>, <span className="doc-code">blocked</span>, <span className="doc-code">cancelled</span>), priority, due dates, and can be assigned to individual team members.</p>

            <h3>Budget & Expenses</h3>
            <p>Track spending against the project budget with line-item expenses:</p>
            <div className="doc-code-block">
                "Log an expense of €3,200 for Cisco switches on the Network Refresh, category hardware"<br />
                "What's the budget status on the Network Refresh project?"<br />
                "Show all expenses for the AV upgrade"
            </div>
            <p>Expense categories: <span className="doc-code">hardware</span>, <span className="doc-code">software</span>, <span className="doc-code">services</span>, <span className="doc-code">labor</span>, <span className="doc-code">travel</span>, <span className="doc-code">other</span>. The AI compares total expenses against the estimated budget when you ask for budget status.</p>

            <h3>Progress Updates</h3>
            <p>Post status updates, flag blockers, and record decisions:</p>
            <div className="doc-code-block">
                "Post an update on Network Refresh: cabling complete on floors 1 and 2"<br />
                "Flag a blocker on the AV project: waiting for vendor delivery"<br />
                "Record a decision: we're going with Cat6a cabling throughout"
            </div>
            <p>Update types: <span className="doc-code">progress</span>, <span className="doc-code">blocker</span>, <span className="doc-code">decision</span>, <span className="doc-code">milestone</span>, <span className="doc-code">general</span>.</p>

            <h3>Linking to Other Entities</h3>
            <p>Connect projects to existing records in the system — assets, tickets, contracts, events, or anything else:</p>
            <div className="doc-code-block">
                "Link the Cisco support contract to the Network Refresh project"<br />
                "Associate asset #42 with the AV upgrade project"
            </div>
            <p>Links use a flexible entity_type + entity_id pattern, so any table in the database can be referenced.</p>

            <div className="doc-callout">
                <strong>Notes & Work Logs:</strong> You can also attach notes and log work time directly against projects and tasks using the existing notes and work_logs tables, which now include optional project_id and project_task_id fields.
            </div>
        </section>
    );
}

function KnowledgeSection() {
    return (
        <section id="knowledge" className="doc-section">
            <h2>Knowledge Management</h2>
            <p>
                TrueCore.cloud provides three tables for capturing and organizing operational knowledge.
            </p>

            <h3>Knowledge Articles</h3>
            <p>
                The <span className="doc-code">knowledge_articles</span> table stores structured guides and reference material:
            </p>
            <ul>
                <li><strong>Types:</strong> <span className="doc-badge">troubleshooting</span> <span className="doc-badge">how_to</span> <span className="doc-badge">sop</span> <span className="doc-badge">reference</span> <span className="doc-badge">faq</span></li>
                <li><strong>Status:</strong> draft, published, or archived</li>
                <li>Includes title, content body, and linked table/asset references</li>
            </ul>

            <h3>Misc Knowledge</h3>
            <p>
                The <span className="doc-code">misc_knowledge</span> table captures operational facts that don't fit into a formal article: office closures, policies, site-specific information, and more.
            </p>
            <ul>
                <li>The AI auto-generates <span className="doc-code">keywords</span> for each entry to improve search</li>
                <li>Can link to a <span className="doc-code">people_involved</span> contact person</li>
                <li>Supports <span className="doc-code">effective_date</span> and <span className="doc-code">expiry_date</span> for time-bound information</li>
            </ul>

            <h3>Workflows</h3>
            <p>
                The <span className="doc-code">workflows</span> table stores step-by-step procedures and processes.
            </p>
            <ul>
                <li>Status: draft, published, or archived</li>
                <li>Can be linked to a <span className="doc-code">contact_person_id</span> for questions</li>
                <li>The AI generates keywords automatically to help with discovery</li>
            </ul>
        </section>
    );
}

function SchemaSection() {
    const groups = [
        {
            title: 'Core Infrastructure',
            tables: [
                { name: 'companies', desc: 'Employers, clients, and vendors', cols: 'id, name, type (employer|client|vendor), category, city, country, website, email, phone, notes' },
                { name: 'sites', desc: 'Client sites/offices', cols: 'id, name, client_id, timezone, city, country, address, notes' },
                { name: 'rooms', desc: 'Spaces within sites', cols: 'id, site_id, name, code, capacity, description' },
            ]
        },
        {
            title: 'People & Teams',
            tables: [
                { name: 'people', desc: 'All persons (employees, contacts, vendor reps, app users)', cols: 'id, first_name, last_name, email, phone, role_title, employer_id, client_id, vendor_id, site_id, is_user, username, user_role, is_supervisor, team_role, notes' },
                { name: 'teams', desc: 'Named groups', cols: 'id, name, site_id, team_type (support|av|operations|management), description' },
                { name: 'pto', desc: 'Leave records', cols: 'id, person_id, leave_type (pto|sick|personal|bereavement|other), start_date, end_date, notes' },
            ]
        },
        {
            title: 'Assets',
            tables: [
                { name: 'assets', desc: 'Physical devices and equipment', cols: 'id, asset_tag, serial_number, asset_type, make, model, lifecycle_status (active|deployed|spare|in_repair|decommissioned|lost), ownership_type, assigned_to_person_id, site_id, room_id, warranty_expiry, purchase_date, important, notes' },
                { name: 'asset_relationships', desc: 'Parent/child asset links', cols: 'id, parent_asset_id, child_asset_id, relationship_type (connected_to|part_of|bundled_with|replaced_by)' },
            ]
        },
        {
            title: 'Support & Issues',
            tables: [
                { name: 'tickets', desc: 'Support tickets and service requests', cols: 'id, title, description, ticket_type (incident|service_request|question|access_request), priority (low|medium|high|critical), status (open|in_progress|pending|resolved|closed), source, requester_person_id, assigned_to_person_id, site_id, related_asset_id, opened_at, resolved_at, closed_at, due_date, important' },
                { name: 'technical_issues', desc: 'Diagnosed technical problems', cols: 'id, title, description, issue_type (hardware|software|network|av|printing|access|other), severity, recurrence_status (one_off|intermittent|recurring|resolved), known_issue, knowledgeworthy, site_id, room_id, related_asset_id, important' },
                { name: 'issue_occurrences', desc: 'Individual sightings of recurring issues', cols: 'id, issue_id, occurred_at, reported_by_person_id, notes' },
            ]
        },
        {
            title: 'Events',
            tables: [
                { name: 'events', desc: 'Meetings, outages, maintenance, vendor visits', cols: 'id, title, description, event_type (meeting|outage|maintenance|audit|vendor_visit|training|deployment|other), status (planned|in_progress|completed|cancelled), impact_level, needs_support, site_id, room_id, start_time, end_time, important' },
                { name: 'event_participants', desc: 'People linked to events', cols: 'id, event_id, person_id, participant_role, attendance_status' },
                { name: 'event_assets', desc: 'Equipment used in events', cols: 'id, event_id, asset_id, notes' },
            ]
        },
        {
            title: 'Notes & Work',
            tables: [
                { name: 'notes', desc: 'Freeform notes on any entity', cols: 'id, content, note_type (general|handover|follow_up|observation|escalation), visibility (internal|client_visible), author_person_id, related_table, related_id, important' },
                { name: 'work_logs', desc: 'Technician time tracking', cols: 'id, description, action_type (troubleshooting|repair|installation|configuration|inspection|consultation|escalation), time_spent_minutes, started_at, ended_at, person_id, related_table, related_id, important' },
            ]
        },
        {
            title: 'Inventory',
            tables: [
                { name: 'inventory_items', desc: 'Catalog of spare parts/consumables', cols: 'id, name, description, item_type (spare_part|consumable|cable|adapter|peripheral|component), sku, unit' },
                { name: 'inventory_stock', desc: 'Current stock levels per item per site', cols: 'id, item_id, site_id, quantity, min_quantity' },
                { name: 'inventory_transactions', desc: 'Audit trail of movements', cols: 'id, item_id, site_id, transaction_type (check_in|check_out|restock|transfer|write_off|adjustment), quantity, performed_by_person_id, notes, important' },
            ]
        },
        {
            title: 'Changes & Contracts',
            tables: [
                { name: 'changes', desc: 'Infrastructure/system changes', cols: 'id, title, description, change_type (standard|emergency|normal), risk_level (low|medium|high), status (planned|approved|in_progress|completed|rolled_back|cancelled), scheduled_start, scheduled_end, owner_person_id, site_id, important' },
                { name: 'vendor_contracts', desc: 'Contracts and SLAs', cols: 'id, vendor_id, title, contract_type, start_date, end_date, value, status, notes' },
            ]
        },
        {
            title: 'Projects',
            tables: [
                { name: 'projects', desc: 'General-purpose project tracking', cols: 'id, name, description, site_id, owner_person_id, status (planned|active|on_hold|completed|cancelled), priority, category, budget_estimated, budget_currency, planned_start, planned_end, actual_start, actual_end, important' },
                { name: 'project_members', desc: 'People involved in projects', cols: 'id, project_id, person_id, role (manager|contributor|stakeholder|observer)' },
                { name: 'project_tasks', desc: 'Nestable work items within projects', cols: 'id, project_id, parent_task_id, title, description, assigned_person_id, status (todo|in_progress|done|blocked|cancelled), priority, due_date, completed_at, sort_order' },
                { name: 'project_updates', desc: 'Progress log entries', cols: 'id, project_id, author_person_id, content, update_type (progress|blocker|decision|milestone|general)' },
                { name: 'project_expenses', desc: 'Budget line items', cols: 'id, project_id, description, amount, currency, category (hardware|software|services|labor|travel|other), expense_date, approved_by_person_id' },
                { name: 'project_links', desc: 'Flexible links to other entities', cols: 'id, project_id, entity_type, entity_id, note' },
            ]
        },
        {
            title: 'Knowledge & Metadata',
            tables: [
                { name: 'knowledge_articles', desc: 'Guides, SOPs, FAQs', cols: 'id, title, content, article_type (troubleshooting|how_to|sop|reference|faq), status (draft|published|archived), author_person_id, related_table, related_id' },
                { name: 'misc_knowledge', desc: 'Operational facts and policies', cols: 'id, title, content, keywords, people_involved, effective_date, expiry_date, important' },
                { name: 'workflows', desc: 'Step-by-step procedures', cols: 'id, title, description, steps, status (draft|published|archived), contact_person_id, keywords, important' },
                { name: 'tags', desc: 'Tag definitions', cols: 'id, name' },
                { name: 'entity_tags', desc: 'Tag assignments', cols: 'id, tag_id, entity_table, entity_id' },
            ]
        },
        {
            title: 'System Tables',
            tables: [
                { name: 'app_settings', desc: 'Application configuration', cols: 'id, key, value' },
                { name: 'chat_sessions', desc: 'Conversation persistence', cols: 'id (UUID), person_id, title, created_at, updated_at' },
                { name: 'chat_messages', desc: 'Message history', cols: 'id, session_id, role, content (JSON), created_at' },
                { name: 'approval_rules', desc: 'Query approval rules', cols: 'id, description, is_active, created_by_person_id, created_at' },
                { name: 'pending_approvals', desc: 'Queued write operations', cols: 'id, sql_statement, explanation, matched_rule_id, status (pending|approved|rejected|failed), submitted_by_person_id, reviewed_by_person_id, review_note' },
                { name: 'audit_log', desc: 'Auto-populated change history (read-only)', cols: 'id, table_name, row_id, action, old_values, new_values, changed_by, changed_at' },
            ]
        },
    ];

    return (
        <section id="schema" className="doc-section">
            <h2>Database Schema</h2>
            <p>
                TrueCore.cloud uses a PostgreSQL database with 30+ tables organized by domain. All write operations are automatically logged to the <span className="doc-code">audit_log</span> table. Below is a reference of every table grouped by function.
            </p>
            {groups.map(g => (
                <div key={g.title}>
                    <h3>{g.title}</h3>
                    <table className="doc-table">
                        <thead><tr><th>Table</th><th>Purpose</th><th>Key Columns</th></tr></thead>
                        <tbody>
                            {g.tables.map(t => (
                                <tr key={t.name}>
                                    <td><span className="doc-badge">{t.name}</span></td>
                                    <td>{t.desc}</td>
                                    <td style={{ fontSize: 12 }}>{t.cols}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ))}
        </section>
    );
}

function ScopeSection() {
    return (
        <section id="scope" className="doc-section">
            <h2>Scope & Limitations</h2>

            <h3>What TrueCore.cloud Covers</h3>
            <p>TrueCore.cloud is purpose-built for <strong>IT and workplace operations</strong> at managed client sites. It handles:</p>
            <ul>
                <li>IT support: issues, tickets, troubleshooting, asset management</li>
                <li>Site operations: rooms, events, maintenance, outages</li>
                <li>People management: teams, contacts, PTO, vendor reps</li>
                <li>Inventory and spare parts tracking</li>
                <li>Change management and vendor contracts</li>
                <li>Project tracking and budget management</li>
                <li>Knowledge capture and documentation</li>
                <li>Work logging and time tracking</li>
                <li>Operational email communications</li>
            </ul>

            <h3>What's Out of Scope</h3>
            <p>TrueCore.cloud will politely decline requests that fall outside its operational domain:</p>
            <ul>
                <li>General knowledge questions ("What's the capital of France?")</li>
                <li>Personal advice or opinions</li>
                <li>Creative writing, coding help, or homework</li>
                <li>News, entertainment, or trivia</li>
                <li>Anything unrelated to IT site operations</li>
            </ul>

            <h3>How the AI Responds to Off-Topic Queries</h3>
            <p>
                If you ask something outside TrueCore.cloud's scope, the AI will briefly explain that it's designed for site operations and suggest how it can help within that domain. It won't attempt to answer off-topic questions.
            </p>

            <div className="doc-callout">
                <strong>Single-site focus:</strong> Each TrueCore.cloud instance is configured for one client site. While data for multiple sites can exist in the database, the AI defaults all operations to the configured home site.
            </div>
        </section>
    );
}

function QATestingSection() {
    return (
        <section id="qa-testing" className="doc-section">
            <h2>QA & Testing</h2>
            <p>
                Manual QA checklist for verifying all TrueCore.cloud features. Each subsection covers a functional area with specific test cases, steps to reproduce, and expected results.
            </p>

            <h3>Prerequisites</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Backend is running</td>
                        <td>Start the FastAPI server and confirm no startup errors in the terminal</td>
                        <td>Server starts on the configured port with no tracebacks</td>
                    </tr>
                    <tr>
                        <td>Frontend is running</td>
                        <td>Start the Vite dev server or serve the production build</td>
                        <td>App loads in the browser with the chat page visible</td>
                    </tr>
                    <tr>
                        <td>Environment variables set</td>
                        <td>Verify <span className="doc-code">ANTHROPIC_API_KEY</span> (and optionally <span className="doc-code">ANTHROPIC_API_KEY_SPARE</span>) and Brevo SMTP variables are configured</td>
                        <td>AI responses stream correctly; spare key failover works on rate limit; email features do not error on missing config</td>
                    </tr>
                </tbody>
            </table>

            <h3>First-Run & Setup</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Bootstrap seed on first launch</td>
                        <td>Start the app with a fresh database and open the chat page</td>
                        <td>The app loads normally with Dublin HQ as the default home site and no setup prompt</td>
                    </tr>
                    <tr>
                        <td>No setup gate before chat</td>
                        <td>On a fresh database, send a message like "Show all assets"</td>
                        <td>The AI processes the request normally without asking you to configure a home site</td>
                    </tr>
                    <tr>
                        <td>Reset restores bootstrap data</td>
                        <td>Use Reset Database, then reopen the chat page</td>
                        <td>The seeded users and Dublin HQ home site are present again immediately</td>
                    </tr>
                </tbody>
            </table>

            <h3>Chat Interface</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Read query</td>
                        <td>Type "Show all people" and press Enter</td>
                        <td>AI returns a formatted list or table of people from the database</td>
                    </tr>
                    <tr>
                        <td>Write command</td>
                        <td>Type "Add John Smith as a new technician" and press Enter</td>
                        <td>AI confirms the insert; SQL operation block shows the INSERT statement</td>
                    </tr>
                    <tr>
                        <td>Streaming response</td>
                        <td>Send any message and observe the response area</td>
                        <td>Typing indicator appears, then text streams in token by token</td>
                    </tr>
                    <tr>
                        <td>New session</td>
                        <td>Click the "+ New" button in the conversation sidebar</td>
                        <td>A fresh conversation starts; previous session appears in the sidebar list</td>
                    </tr>
                    <tr>
                        <td>Resume session</td>
                        <td>Click a previous session in the sidebar</td>
                        <td>Chat history loads with all prior messages and SQL blocks intact</td>
                    </tr>
                    <tr>
                        <td>SQL operation panel</td>
                        <td>After a write command, click the collapsible SQL block</td>
                        <td>Block expands to show the SQL executed, explanation, and result</td>
                    </tr>
                    <tr>
                        <td>Markdown rendering</td>
                        <td>Ask the AI a question that produces a list or table (e.g., "Summarize open requests")</td>
                        <td>Response renders bold, lists, tables, and inline code correctly</td>
                    </tr>
                </tbody>
            </table>

            <h3>Approval System</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Create approval rule (admin)</td>
                        <td>As admin, type "Add an approval rule: any changes to the assets table need approval"</td>
                        <td>AI confirms the rule is created and active</td>
                    </tr>
                    <tr>
                        <td>Write queued for approval (user)</td>
                        <td>As a standard user, type "Add a new laptop asset with serial XYZ"</td>
                        <td>AI confirms the write was queued for admin approval instead of executing</td>
                    </tr>
                    <tr>
                        <td>Approve pending write</td>
                        <td>As admin, type "Show pending approvals" then "Approve approval #1"</td>
                        <td>Pending item shown; after approval the SQL executes and status changes to approved</td>
                    </tr>
                    <tr>
                        <td>Reject pending write</td>
                        <td>As admin, type "Reject approval #2 with note: not authorized"</td>
                        <td>Approval status changes to rejected; the SQL is never executed</td>
                    </tr>
                </tbody>
            </table>

            <h3>Dashboard</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Stat cards display</td>
                        <td>Navigate to the Dashboard page</td>
                        <td>Five stat cards show counts for Active Assets, Open Tickets, Open Issues, Events This Week, and Important Items</td>
                    </tr>
                    <tr>
                        <td>Charts render</td>
                        <td>Scroll to the charts section on the Dashboard</td>
                        <td>Four charts render: Assets by Period, Issues Summary, Vendor Visits, Staff per Site</td>
                    </tr>
                    <tr>
                        <td>Data accuracy after changes</td>
                        <td>Add a new asset via chat, then navigate to the Dashboard</td>
                        <td>Active Assets count increments by 1; Assets by Period chart reflects the new entry</td>
                    </tr>
                </tbody>
            </table>

            <h3>Database Browser</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Table list</td>
                        <td>Navigate to the Database page</td>
                        <td>Left sidebar lists all database tables with row counts</td>
                    </tr>
                    <tr>
                        <td>Schema display</td>
                        <td>Click any table in the sidebar</td>
                        <td>Schema bar at the top shows column names, types, PK markers, and NOT NULL constraints</td>
                    </tr>
                    <tr>
                        <td>Pagination</td>
                        <td>Select a table with more than 50 rows; click Next/Previous</td>
                        <td>Data pages through 50 rows at a time; page indicator updates</td>
                    </tr>
                    <tr>
                        <td>Insert row</td>
                        <td>Click "Add Row", fill in the form, and submit</td>
                        <td>New row appears in the data grid; row count increments</td>
                    </tr>
                    <tr>
                        <td>Delete row</td>
                        <td>Hover over a row and click the red delete button</td>
                        <td>Row is removed from the grid; row count decrements</td>
                    </tr>
                    <tr>
                        <td>Create table</td>
                        <td>Click "Create Table", define columns, and submit</td>
                        <td>New table appears in the sidebar list</td>
                    </tr>
                </tbody>
            </table>

            <h3>Database Management</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Export to Excel</td>
                        <td>Click "Export to Excel" on the Dashboard or Database page</td>
                        <td>Browser downloads a valid <span className="doc-code">.xlsx</span> file with all tables</td>
                    </tr>
                    <tr>
                        <td>Export to Excel</td>
                        <td>Click "Export to Excel"</td>
                        <td>Browser downloads a <span className="doc-code">.xlsx</span> file with one sheet per table</td>
                    </tr>
                    <tr>
                        <td>Import & Merge (.xlsx)</td>
                        <td>Click "Import Merge" and upload a previously exported <span className="doc-code">.xlsx</span> file</td>
                        <td>Data is merged into existing tables; no duplicates created for matching rows</td>
                    </tr>
                </tbody>
            </table>

            <h3>CSV Upload</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Stage CSV via chat</td>
                        <td>Click the paperclip button and select a <span className="doc-code">.csv</span> file</td>
                        <td>File uploads; AI receives the filename, headers, row count, and sample data</td>
                    </tr>
                    <tr>
                        <td>Preview and mapping</td>
                        <td>After uploading, the AI proposes a column mapping</td>
                        <td>AI presents a mapping of CSV columns to database table columns and asks for confirmation</td>
                    </tr>
                    <tr>
                        <td>AI-driven import</td>
                        <td>Confirm the proposed mapping</td>
                        <td>Data is imported; AI reports the number of rows inserted and any skipped columns</td>
                    </tr>
                </tbody>
            </table>

            <h3>User Roles</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Admin vs User switching</td>
                        <td>Use the user switcher button in the conversation sidebar</td>
                        <td>User context changes; admin-only features appear or disappear accordingly</td>
                    </tr>
                    <tr>
                        <td>Permission enforcement</td>
                        <td>As a standard user, try "Create an approval rule" or "Reset the database"</td>
                        <td>AI denies the action and explains it requires admin privileges</td>
                    </tr>
                    <tr>
                        <td>Approval badge</td>
                        <td>As admin with pending approvals, check the Chat nav link</td>
                        <td>Badge shows the count of pending approvals; disappears when all are resolved</td>
                    </tr>
                </tbody>
            </table>

            <h3>Email & Daily Reports</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Send email via chat</td>
                        <td>Type "Email John about the scheduled maintenance tomorrow"</td>
                        <td>AI looks up John's email, composes and sends the email; confirmation shown in SQL block</td>
                    </tr>
                    <tr>
                        <td>Manual daily report trigger</td>
                        <td>As admin, click "Send Daily Report" on the Dashboard</td>
                        <td>Report is generated and emailed to all supervisors; success message displayed</td>
                    </tr>
                </tbody>
            </table>

            <h3>Edge Cases & Error Handling</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Invalid file upload</td>
                        <td>Try to upload a non-CSV file (e.g., <span className="doc-code">.png</span>) via the paperclip button</td>
                        <td>Upload is rejected or AI reports the file is not a valid CSV</td>
                    </tr>
                    <tr>
                        <td>Empty CSV</td>
                        <td>Upload a CSV file with headers but no data rows</td>
                        <td>AI reports that the file contains no data to import</td>
                    </tr>
                    <tr>
                        <td>SQL injection in table names</td>
                        <td>Try creating a table with a name like <span className="doc-code">'; DROP TABLE people;--</span></td>
                        <td>Input is sanitized or rejected; no tables are dropped</td>
                    </tr>
                    <tr>
                        <td>Long messages</td>
                        <td>Send a very long message (1000+ characters) in the chat</td>
                        <td>Message is accepted and processed without truncation or UI breakage</td>
                    </tr>
                </tbody>
            </table>

            <h3>Reset Database</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Admin-only access</td>
                        <td>As a standard user, check the Dashboard for the Reset Database button</td>
                        <td>Button is not visible to non-admin users</td>
                    </tr>
                    <tr>
                        <td>Reset recreates tables</td>
                        <td>As admin, click "Reset Database" on the Dashboard</td>
                        <td>All data is deleted; tables are recreated from the schema; app returns to first-run state</td>
                    </tr>
                </tbody>
            </table>

            <div className="doc-callout doc-callout--tip">
                <strong>Tip:</strong> Run through these test cases after any major change to verify nothing has regressed. Start with Prerequisites, then work through each section in order.
            </div>
        </section>
    );
}

function RoadmapSection() {
    return (
        <section id="roadmap" className="doc-section">
            <h2>Roadmap</h2>
            <p>
                Current status: <strong>Core platform complete</strong> — chat, database browser, dashboard, authentication, approval system, CSV import, email, knowledge management, and mobile responsiveness are all functional. Focus is on knowledge UI and advanced features.
            </p>

            <h3>Phase 1: Core MVP (Complete)</h3>
            <div className="doc-callout doc-callout--tip">
                <strong>Goal:</strong> Users can interact with their site database through natural language, browse data visually, and get a high-level overview of operations.
            </div>
            <ul>
                <li><strong>AI Chat with Claude</strong> — Streaming responses, tool use (database queries, knowledge lookups), session-based conversations</li>
                <li><strong>Database Browser</strong> — Table viewing with pagination, Excel import/export</li>
                <li><strong>Dashboard</strong> — Overview stats and charts via Recharts</li>
                <li><strong>User Roles</strong> — Admin/user distinction with role-based visibility</li>
                <li><strong>Daily Email Reports</strong> — Automated reports via Brevo SMTP</li>
                <li><strong>Chat Session Persistence</strong> — Conversations saved and resumable across page loads</li>
            </ul>

            <h3>Phase 2: Polish & Complete (Complete)</h3>
            <div className="doc-callout doc-callout--tip">
                <strong>Goal:</strong> Finish partially-built features so the core experience feels complete and reliable.
            </div>
            <ul>
                <li><strong>Approval Workflow</strong> — Admin-defined rules, automatic query interception, approve/reject pending operations</li>
                <li><strong>CSV Import</strong> — AI-powered column mapping with validation, approval integration, and retry on failure</li>
                <li><strong>Table Creation / Column Addition</strong> — Backend routes and frontend modals for creating new tables and adding columns</li>
                <li><strong>SQL Safety Policies</strong> — Destructive operations (DROP, TRUNCATE, ALTER DROP/RENAME) are system-blocked; protected tables require WHERE clauses</li>
                <li><strong>Excel Generation</strong> — AI can generate downloadable .xlsx files from query results</li>
                <li><strong>User Invitations</strong> — Instance owners can invite new users via email</li>
            </ul>

            <h3>Phase 3: Knowledge & Content (Next)</h3>
            <div className="doc-callout doc-callout--tip">
                <strong>Goal:</strong> Users can build and maintain a structured knowledge base alongside their operational data, making the AI assistant more useful over time.
            </div>
            <ul>
                <li><strong>Knowledge Article Management</strong> — Full CRUD UI for <span className="doc-code">knowledge_articles</span> (create, edit, view, delete)</li>
                <li><strong>Tag System UI</strong> — Apply and filter tags across entities (articles, tables, records)</li>
                <li><strong>Workflow Documentation</strong> — Viewer/editor for standard operating procedures and workflows</li>
                <li><strong>Site-Specific Notes</strong> — Miscellaneous knowledge and notes interface for capturing institutional knowledge</li>
            </ul>

            <h3>Phase 4: Production Readiness (In Progress)</h3>
            <div className="doc-callout doc-callout--tip">
                <strong>Goal:</strong> The application is secure, deployable, and suitable for real-world use beyond development.
            </div>
            <ul>
                <li><s><strong>Authentication & Login</strong></s> — Complete: proper authentication with login, signup, sessions, and multi-instance support</li>
                <li><s><strong>Mobile Responsiveness</strong></s> — Complete: fully responsive layout with hamburger navigation and off-canvas sidebars</li>
                <li><s><strong>PostgreSQL Migration</strong></s> — Complete: migrated from SQLite to PostgreSQL with connection pooling and Row-Level Security</li>
                <li><strong>Deployment Pipeline</strong> — Dockerfile, docker-compose, CI/CD configuration</li>
                <li><strong>Security Audit</strong> — CORS lockdown, input sanitization, dependency audit, OWASP review</li>
            </ul>

            <h3>Future Ideas</h3>
            <div className="doc-callout">
                <strong>Goal:</strong> Stretch goals and backlog items to explore once the core product is solid.
            </div>
            <ul>
                <li><strong>Real-Time Notifications</strong> — WebSocket-based alerts for approvals, report completions, and system events</li>
                <li><strong>Audit Log Viewer</strong> — UI for browsing the audit trail of all data changes</li>
                <li><strong>Advanced Reporting</strong> — Scheduled report customization, custom queries, export options</li>
                <li><strong>Role-Based Access Control</strong> — Granular permissions beyond the current admin/user/owner split</li>
                <li><strong>Home Site Setup Wizard</strong> — Guided first-run experience for configuring a new site</li>
            </ul>
        </section>
    );
}

function CostEstimateSection() {
    return (
        <section id="cost-estimate" className="doc-section">
            <h2>Cost Estimate</h2>
            <div style={{
                background: '#ffeb3b',
                border: '1px solid #fdd835',
                borderLeft: '4px solid #f9a825',
                borderRadius: '6px',
                padding: '12px 16px',
                marginBottom: '20px',
                fontSize: '0.95em',
                color: '#000000'
            }}>
                <strong style={{ color: '#8b0000' }}>Model Recommendation:</strong> TrueCore.cloud has been tested with both Sonnet and Opus models. Although Sonnet is 5 times cheaper than Opus, the performance has been very similar, so the recommendation is to run TrueCore.cloud with the Sonnet 4.6 model for decreased costs and the same performance. No testing has been done with OpenAI LLMs.
            </div>
            <p>
                TrueCore.cloud runs on a single AWS EC2 instance with a PostgreSQL database and uses the Claude API for its AI assistant. The Claude API is the dominant cost driver, accounting for 85–97% of total monthly spend depending on usage volume.
            </p>

            <h3>Claude API Cost Analysis</h3>
            <p>
                Each user message triggers an <strong>agentic loop</strong>: Claude receives the message, calls one or more tools (SQL queries, email sends), receives tool results, and generates a final response. On average this means <strong>~2 API calls per user message</strong>.
            </p>

            <h4>Per-Message Token Breakdown</h4>
            <table className="doc-table">
                <thead>
                    <tr><th>Component</th><th>Tokens</th><th>Notes</th></tr>
                </thead>
                <tbody>
                    <tr><td>System prompt</td><td>~5,400</td><td>Full prompt + schema DDL. Cached with 5-min TTL.</td></tr>
                    <tr><td>Tool definitions</td><td>~250</td><td>7 tool schemas</td></tr>
                    <tr><td>Non-cached input</td><td>~4,000</td><td>User message + conversation history + tool results</td></tr>
                    <tr><td>Cached reads</td><td>~10,800</td><td>System prompt from cache on both calls (~5,400 × 2). 90% hit rate.</td></tr>
                    <tr><td>Cache writes</td><td>~540</td><td>System prompt written to cache on ~10% of requests</td></tr>
                    <tr><td>Output tokens</td><td>~2,300</td><td>Tool-use call (~300) + final response (~2,000)</td></tr>
                </tbody>
            </table>

            <h4>Claude API Pricing</h4>
            <table className="doc-table">
                <thead>
                    <tr><th></th><th>Sonnet 4</th><th>Opus 4</th></tr>
                </thead>
                <tbody>
                    <tr><td>Input tokens</td><td>$3.00 / MTok</td><td>$15.00 / MTok</td></tr>
                    <tr><td>Output tokens</td><td>$15.00 / MTok</td><td>$75.00 / MTok</td></tr>
                    <tr><td>Cache write</td><td>$3.75 / MTok</td><td>$18.75 / MTok</td></tr>
                    <tr><td>Cache read</td><td>$0.30 / MTok</td><td>$1.50 / MTok</td></tr>
                </tbody>
            </table>
            <p><em>MTok = 1 million tokens. Pricing as of early 2025.</em></p>

            <h4>Per-Message Cost</h4>
            <p><strong>Sonnet 4:</strong></p>
            <table className="doc-table">
                <thead>
                    <tr><th>Component</th><th>Tokens</th><th>Rate</th><th>Cost</th></tr>
                </thead>
                <tbody>
                    <tr><td>Non-cached input</td><td>4,000</td><td>$3.00/MTok</td><td>$0.0120</td></tr>
                    <tr><td>Cached reads</td><td>10,800</td><td>$0.30/MTok</td><td>$0.0032</td></tr>
                    <tr><td>Cache writes</td><td>540</td><td>$3.75/MTok</td><td>$0.0020</td></tr>
                    <tr><td>Output</td><td>2,300</td><td>$15.00/MTok</td><td>$0.0345</td></tr>
                    <tr><td><strong>Total per message</strong></td><td></td><td></td><td><strong>~$0.052</strong></td></tr>
                </tbody>
            </table>
            <p><strong>Opus 4:</strong></p>
            <table className="doc-table">
                <thead>
                    <tr><th>Component</th><th>Tokens</th><th>Rate</th><th>Cost</th></tr>
                </thead>
                <tbody>
                    <tr><td>Non-cached input</td><td>4,000</td><td>$15.00/MTok</td><td>$0.0600</td></tr>
                    <tr><td>Cached reads</td><td>10,800</td><td>$1.50/MTok</td><td>$0.0162</td></tr>
                    <tr><td>Cache writes</td><td>540</td><td>$18.75/MTok</td><td>$0.0101</td></tr>
                    <tr><td>Output</td><td>2,300</td><td>$75.00/MTok</td><td>$0.1725</td></tr>
                    <tr><td><strong>Total per message</strong></td><td></td><td></td><td><strong>~$0.259</strong></td></tr>
                </tbody>
            </table>

            <h4>Monthly API Cost by Usage Tier</h4>
            <p>Based on 22 business days per month:</p>
            <table className="doc-table">
                <thead>
                    <tr><th>Tier</th><th>Users</th><th>Msgs/User/Day</th><th>Msgs/Day</th><th>Msgs/Month</th><th>Sonnet 4/mo</th><th>Opus 4/mo</th></tr>
                </thead>
                <tbody>
                    <tr><td>Light</td><td>5</td><td>20</td><td>100</td><td>2,200</td><td><strong>$114</strong></td><td><strong>$569</strong></td></tr>
                    <tr><td>Medium</td><td>15</td><td>30</td><td>450</td><td>9,900</td><td><strong>$512</strong></td><td><strong>$2,562</strong></td></tr>
                    <tr><td>Heavy</td><td>50</td><td>40</td><td>2,000</td><td>44,000</td><td><strong>$2,275</strong></td><td><strong>$11,387</strong></td></tr>
                </tbody>
            </table>

            <h3>AWS EC2 Costs</h3>
            <p>TrueCore.cloud runs on a single EC2 instance with PostgreSQL running on the same host.</p>

            <h4>Instance Sizing</h4>
            <table className="doc-table">
                <thead>
                    <tr><th>Tier</th><th>Instance</th><th>vCPUs</th><th>RAM</th><th>On-Demand/mo</th><th>Reserved 1yr/mo</th><th>Savings</th></tr>
                </thead>
                <tbody>
                    <tr><td>Light</td><td>t3.small</td><td>2</td><td>2 GB</td><td>$15.18</td><td>$9.64</td><td>37%</td></tr>
                    <tr><td>Medium</td><td>t3.medium</td><td>2</td><td>4 GB</td><td>$30.37</td><td>$19.27</td><td>37%</td></tr>
                    <tr><td>Heavy</td><td>t3.large</td><td>2</td><td>8 GB</td><td>$60.74</td><td>$38.54</td><td>37%</td></tr>
                </tbody>
            </table>
            <p><em>Prices for us-east-1, Linux, on-demand vs. 1-year standard reserved (no upfront).</em></p>

            <h4>Storage (EBS)</h4>
            <table className="doc-table">
                <thead>
                    <tr><th>Tier</th><th>Volume</th><th>Size</th><th>Monthly Cost</th></tr>
                </thead>
                <tbody>
                    <tr><td>Light</td><td>gp3</td><td>20 GB</td><td>$1.60</td></tr>
                    <tr><td>Medium</td><td>gp3</td><td>30 GB</td><td>$2.40</td></tr>
                    <tr><td>Heavy</td><td>gp3</td><td>50 GB</td><td>$4.00</td></tr>
                </tbody>
            </table>

            <h4>Data Transfer</h4>
            <table className="doc-table">
                <thead>
                    <tr><th>Tier</th><th>Estimated Outbound</th><th>Monthly Cost</th></tr>
                </thead>
                <tbody>
                    <tr><td>Light</td><td>~5 GB</td><td>$0.45</td></tr>
                    <tr><td>Medium</td><td>~10 GB</td><td>$0.90</td></tr>
                    <tr><td>Heavy</td><td>~20 GB</td><td>$1.80</td></tr>
                </tbody>
            </table>

            <h3>Other Costs</h3>
            <table className="doc-table">
                <thead>
                    <tr><th>Item</th><th>Monthly Cost</th><th>Notes</th></tr>
                </thead>
                <tbody>
                    <tr><td>Domain registration</td><td>~$1.00</td><td>Amortized from ~$12/year</td></tr>
                    <tr><td>SSL/TLS certificate</td><td>$0.00</td><td>Let's Encrypt (free, auto-renewing)</td></tr>
                    <tr><td>Brevo SMTP</td><td>$0.00</td><td>Free tier: 300 emails/day</td></tr>
                    <tr><td>S3 backups</td><td>$0.50–$2.00</td><td>Daily PostgreSQL backups (&lt;100 MB)</td></tr>
                    <tr><td>Route 53 DNS</td><td>$0.50</td><td>$0.50/hosted zone + negligible query costs</td></tr>
                </tbody>
            </table>
            <p><strong>Total other costs: ~$2.00–$3.50/month</strong></p>

            <h3>Monthly Summary</h3>

            <h4>Light Usage (5 users, 100 msgs/day)</h4>
            <table className="doc-table">
                <thead>
                    <tr><th>Component</th><th>Sonnet 4</th><th>Opus 4</th></tr>
                </thead>
                <tbody>
                    <tr><td>Claude API</td><td>$114.00</td><td>$569.00</td></tr>
                    <tr><td>EC2 (t3.small, on-demand)</td><td>$15.18</td><td>$15.18</td></tr>
                    <tr><td>EBS (20 GB gp3)</td><td>$1.60</td><td>$1.60</td></tr>
                    <tr><td>Data transfer</td><td>$0.45</td><td>$0.45</td></tr>
                    <tr><td>Other (domain, S3, Route 53)</td><td>$2.50</td><td>$2.50</td></tr>
                    <tr><td><strong>Monthly total</strong></td><td><strong>$133.73</strong></td><td><strong>$588.73</strong></td></tr>
                    <tr><td><strong>Annual total</strong></td><td><strong>$1,605</strong></td><td><strong>$7,065</strong></td></tr>
                    <tr><td>API as % of total</td><td>85%</td><td>97%</td></tr>
                </tbody>
            </table>

            <h4>Medium Usage (15 users, 450 msgs/day)</h4>
            <table className="doc-table">
                <thead>
                    <tr><th>Component</th><th>Sonnet 4</th><th>Opus 4</th></tr>
                </thead>
                <tbody>
                    <tr><td>Claude API</td><td>$512.00</td><td>$2,562.00</td></tr>
                    <tr><td>EC2 (t3.medium, on-demand)</td><td>$30.37</td><td>$30.37</td></tr>
                    <tr><td>EBS (30 GB gp3)</td><td>$2.40</td><td>$2.40</td></tr>
                    <tr><td>Data transfer</td><td>$0.90</td><td>$0.90</td></tr>
                    <tr><td>Other (domain, S3, Route 53)</td><td>$3.00</td><td>$3.00</td></tr>
                    <tr><td><strong>Monthly total</strong></td><td><strong>$548.67</strong></td><td><strong>$2,598.67</strong></td></tr>
                    <tr><td><strong>Annual total</strong></td><td><strong>$6,584</strong></td><td><strong>$31,184</strong></td></tr>
                    <tr><td>API as % of total</td><td>93%</td><td>99%</td></tr>
                </tbody>
            </table>

            <h4>Heavy Usage (50 users, 2,000 msgs/day)</h4>
            <table className="doc-table">
                <thead>
                    <tr><th>Component</th><th>Sonnet 4</th><th>Opus 4</th></tr>
                </thead>
                <tbody>
                    <tr><td>Claude API</td><td>$2,275.00</td><td>$11,387.00</td></tr>
                    <tr><td>EC2 (t3.large, on-demand)</td><td>$60.74</td><td>$60.74</td></tr>
                    <tr><td>EBS (50 GB gp3)</td><td>$4.00</td><td>$4.00</td></tr>
                    <tr><td>Data transfer</td><td>$1.80</td><td>$1.80</td></tr>
                    <tr><td>Other (domain, S3, Route 53)</td><td>$3.50</td><td>$3.50</td></tr>
                    <tr><td><strong>Monthly total</strong></td><td><strong>$2,345.04</strong></td><td><strong>$11,457.04</strong></td></tr>
                    <tr><td><strong>Annual total</strong></td><td><strong>$28,140</strong></td><td><strong>$137,484</strong></td></tr>
                    <tr><td>API as % of total</td><td>97%</td><td>99%</td></tr>
                </tbody>
            </table>

            <h4>With Reserved Instances (1-Year, No Upfront)</h4>
            <p>Switching from on-demand to 1-year reserved instances saves ~37% on EC2:</p>
            <table className="doc-table">
                <thead>
                    <tr><th>Tier</th><th>Sonnet Monthly (RI)</th><th>Opus Monthly (RI)</th><th>EC2 Savings/yr</th></tr>
                </thead>
                <tbody>
                    <tr><td>Light</td><td>$128.19</td><td>$583.19</td><td>$66</td></tr>
                    <tr><td>Medium</td><td>$537.57</td><td>$2,587.57</td><td>$133</td></tr>
                    <tr><td>Heavy</td><td>$2,322.84</td><td>$11,434.84</td><td>$266</td></tr>
                </tbody>
            </table>

            <h3>Key Observations</h3>
            <div className="doc-callout">
                <ul>
                    <li><strong>API costs dominate everything.</strong> Claude API accounts for 85–99% of total spend. Infrastructure optimization has minimal impact on the overall bill.</li>
                    <li><strong>Opus is ~5x more expensive than Sonnet.</strong> The default model is Sonnet. Switching to Opus should only be done if the quality improvement justifies a 5x cost increase.</li>
                    <li><strong>Prompt caching saves ~90% on system prompt reads.</strong> The system prompt is cached with a 5-minute TTL. At Sonnet rates, this saves ~$0.014 per message vs. uncached reads (~$139/month saved at medium tier).</li>
                    <li><strong>The agentic loop amplifies costs.</strong> Each tool call triggers another full API round-trip. A simple query costs ~$0.052, but a complex multi-step operation (3–4 tool calls) could cost $0.10–$0.15.</li>
                    <li><strong>No scheduled API costs.</strong> Daily reports use direct SQL + Brevo SMTP — they do not call the Claude API.</li>
                    <li><strong>PostgreSQL runs locally on the same instance.</strong> No RDS or managed database service needed.</li>
                    <li><strong>Email is effectively free.</strong> Brevo's free tier (300 emails/day) covers daily reports and ad-hoc sends with significant headroom.</li>
                </ul>
            </div>

            <h3>Assumptions</h3>
            <ul>
                <li>22 business days per month for message volume calculations</li>
                <li>us-east-1 region for all AWS pricing</li>
                <li>90% prompt cache hit rate — realistic for active users within the 5-minute ephemeral window</li>
                <li>Average 2 API calls per user message (1 initial + 1 tool-use follow-up)</li>
                <li><span className="doc-code">max_tokens=4096</span> per API call — actual output is typically much shorter (~300–2,000 tokens)</li>
                <li>Conversation history grows over a session — the 4,000 non-cached input token estimate accounts for average conversation context</li>
                <li>AWS and Claude API pricing as of early 2025</li>
                <li>Single-instance deployment — no load balancing, auto-scaling, or multi-AZ redundancy</li>
                <li>Brevo free tier — 300 emails/day limit; upgrade to paid plan ($9/mo) only if needed</li>
            </ul>
        </section>
    );
}
