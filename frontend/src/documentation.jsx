import { useState, useEffect, useRef } from 'react';

const TOC = [
    { id: 'overview', label: 'Overview' },
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
    { id: 'knowledge', label: 'Knowledge Management' },
    { id: 'schema', label: 'Database Schema' },
    { id: 'scope', label: 'Scope & Limitations' },
    { id: 'qa-testing', label: 'QA & Testing' },
    { id: 'roadmap', label: 'Roadmap' },
];

export function DocumentationPage() {
    const [activeId, setActiveId] = useState('overview');
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
    };

    return (
        <div className="doc-layout">
            <nav className="doc-sidebar">
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
                <KnowledgeSection />
                <SchemaSection />
                <ScopeSection />
                <QATestingSection />
                <RoadmapSection />
            </div>
        </div>
    );
}

function OverviewSection() {
    return (
        <section id="overview" className="doc-section">
            <h2>Overview</h2>
            <p>
                MileCore is an AI-powered database assistant built for technical site operations. It helps IT support teams, tech bar technicians, AV support, and workplace technology teams store and retrieve operational data through natural language conversation.
            </p>
            <h3>Tech Stack</h3>
            <ul>
                <li><strong>Backend:</strong> Python with FastAPI, SQLite database</li>
                <li><strong>AI:</strong> Anthropic Claude via streaming API</li>
                <li><strong>Frontend:</strong> React (Vite), Recharts for dashboard visualizations</li>
                <li><strong>Email:</strong> Brevo SMTP relay</li>
            </ul>
            <h3>Getting Started</h3>
            <p>
                When MileCore launches for the first time, it will prompt you to configure a <strong>home site</strong>. This is the client location this instance manages (e.g., "Workday Dublin" or "Google Paris"). All operations default to the home site unless you specify otherwise.
            </p>
            <div className="doc-callout">
                <strong>Home site setup is required.</strong> MileCore will not process other requests until a home site is configured. Simply type the client name and city when prompted.
            </div>
            <h3>Core Workflow</h3>
            <p>MileCore is organized around the lifecycle of site operations:</p>
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

function ChatSection() {
    return (
        <section id="chat" className="doc-section">
            <h2>Chat Interface</h2>
            <p>
                The chat page is the primary way to interact with MileCore. Type natural language messages and the AI will translate your intent into database operations.
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
                MileCore understands natural language requests across many operational domains. Here's what you can ask, organized by category.
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
                MileCore supports bulk data import via CSV files. The AI analyzes your file, maps columns to the target table, and imports the data.
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
                Only admin users can manage approval rules. Ask MileCore to create a rule by describing what should require approval:
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
                The Database page provides a visual interface for browsing, editing, and managing all tables in the MileCore database.
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
                <li><strong>Download DB:</strong> Downloads the raw SQLite <span className="doc-code">.db</span> file</li>
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
                <li><strong>Open Requests</strong> &mdash; requests with status 'open' or 'in_progress'</li>
                <li><strong>Open Issues</strong> &mdash; technical issues not yet resolved</li>
                <li><strong>Events This Week</strong> &mdash; events scheduled in the current week</li>
                <li><strong>Important Items</strong> &mdash; total items flagged as important across all tables</li>
            </ul>

            <h3>Charts</h3>
            <p>Four visualization panels powered by Recharts:</p>
            <ul>
                <li><strong>Assets by Period</strong> &mdash; assets created per day over the last 30 days (area chart)</li>
                <li><strong>Issues Summary</strong> &mdash; requests by status and issues by severity (bar charts)</li>
                <li><strong>Vendor Visits</strong> &mdash; vendor visit events grouped by status (bar chart)</li>
                <li><strong>Staff per Site</strong> &mdash; employee count at each site (bar chart)</li>
            </ul>

            <h3>Database Management</h3>
            <p>A management panel at the bottom provides:</p>
            <ul>
                <li><strong>Export to Excel</strong> &mdash; download all data as <span className="doc-code">.xlsx</span></li>
                <li><strong>Import Merge</strong> &mdash; upload an Excel or <span className="doc-code">.db</span> file to merge data into existing tables</li>
                <li><strong>Download DB</strong> &mdash; download the raw SQLite database file</li>
            </ul>

            <h3>Admin Actions</h3>
            <p>Admin users see additional buttons:</p>
            <ul>
                <li><strong>Send Daily Report</strong> &mdash; manually triggers the daily report email to all supervisors</li>
                <li><strong>Reset Database</strong> &mdash; re-initializes the database from schema (destroys all data)</li>
            </ul>
            <div className="doc-callout doc-callout--warning">
                <strong>Warning:</strong> Reset Database is destructive and cannot be undone. It drops all data and recreates tables from the schema definition.
            </div>
        </section>
    );
}

function EmailSection() {
    return (
        <section id="email" className="doc-section">
            <h2>Email</h2>
            <p>
                MileCore can send emails on your behalf through the <span className="doc-code">send_email</span> tool. Emails are sent via Brevo (formerly Sendinblue) SMTP relay.
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
        </section>
    );
}

function UserRolesSection() {
    return (
        <section id="user-roles" className="doc-section">
            <h2>User Roles</h2>
            <p>
                MileCore has two user roles that control access to administrative features.
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

            <h3>Demo User Switching</h3>
            <p>
                In the demo environment, you can switch between users using the button in the conversation sidebar. This toggles between two pre-configured people (person_id 1 and 2) with different roles, letting you test admin vs. standard user behavior.
            </p>

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
                MileCore automatically generates and sends daily site reports via email to designated supervisors.
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
                {['technical_issues', 'requests', 'events', 'notes', 'changes', 'work_logs', 'assets', 'inventory_transactions', 'misc_knowledge', 'workflows'].map(t => (
                    <span key={t} className="doc-badge">{t}</span>
                ))}
            </div>

            <h3>Flagging & Unflagging</h3>
            <p>Use natural language to manage flags:</p>
            <div className="doc-code-block">
                "Flag request #5 as important"<br />
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

function KnowledgeSection() {
    return (
        <section id="knowledge" className="doc-section">
            <h2>Knowledge Management</h2>
            <p>
                MileCore provides three tables for capturing and organizing operational knowledge.
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
                { name: 'people', desc: 'All persons (employees, contacts, vendor reps, app users)', cols: 'id, first_name, last_name, email, phone, job_title, employer_id, client_id, vendor_id, site_id, is_user, username, user_role, is_supervisor, team_role, notes' },
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
                { name: 'requests', desc: 'Support tickets and service requests', cols: 'id, title, description, request_type (incident|service_request|question|access_request), priority (low|medium|high|critical), status (open|in_progress|pending|resolved|closed), source, requester_person_id, assigned_to_person_id, site_id, related_asset_id, opened_at, resolved_at, closed_at, important' },
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
                MileCore uses a SQLite database with 30+ tables organized by domain. All write operations are automatically logged to the <span className="doc-code">audit_log</span> table. Below is a reference of every table grouped by function.
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

            <h3>What MileCore Covers</h3>
            <p>MileCore is purpose-built for <strong>IT and workplace operations</strong> at managed client sites. It handles:</p>
            <ul>
                <li>IT support: issues, requests, troubleshooting, asset management</li>
                <li>Site operations: rooms, events, maintenance, outages</li>
                <li>People management: teams, contacts, PTO, vendor reps</li>
                <li>Inventory and spare parts tracking</li>
                <li>Change management and vendor contracts</li>
                <li>Knowledge capture and documentation</li>
                <li>Work logging and time tracking</li>
                <li>Operational email communications</li>
            </ul>

            <h3>What's Out of Scope</h3>
            <p>MileCore will politely decline requests that fall outside its operational domain:</p>
            <ul>
                <li>General knowledge questions ("What's the capital of France?")</li>
                <li>Personal advice or opinions</li>
                <li>Creative writing, coding help, or homework</li>
                <li>News, entertainment, or trivia</li>
                <li>Anything unrelated to IT site operations</li>
            </ul>

            <h3>How the AI Responds to Off-Topic Queries</h3>
            <p>
                If you ask something outside MileCore's scope, the AI will briefly explain that it's designed for site operations and suggest how it can help within that domain. It won't attempt to answer off-topic questions.
            </p>

            <div className="doc-callout">
                <strong>Single-site focus:</strong> Each MileCore instance is configured for one client site. While data for multiple sites can exist in the database, the AI defaults all operations to the configured home site.
            </div>
        </section>
    );
}

function QATestingSection() {
    return (
        <section id="qa-testing" className="doc-section">
            <h2>QA & Testing</h2>
            <p>
                Manual QA checklist for verifying all MileCore features. Each subsection covers a functional area with specific test cases, steps to reproduce, and expected results.
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
                        <td>Verify <span className="doc-code">ANTHROPIC_API_KEY</span> and Brevo SMTP variables are configured</td>
                        <td>AI responses stream correctly; email features do not error on missing config</td>
                    </tr>
                </tbody>
            </table>

            <h3>First-Run & Setup</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Home site prompt on first launch</td>
                        <td>Start the app with a fresh database and open the chat page</td>
                        <td>AI prompts you to configure a home site before accepting other requests</td>
                    </tr>
                    <tr>
                        <td>Configure home site</td>
                        <td>Type a client name and city (e.g., "Workday Dublin") when prompted</td>
                        <td>AI confirms the home site is set; subsequent requests work normally</td>
                    </tr>
                    <tr>
                        <td>Blocks requests before setup</td>
                        <td>On a fresh database, send a non-setup message like "Show all assets"</td>
                        <td>AI redirects you to configure the home site first</td>
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
                        <td>Five stat cards show counts for Active Assets, Open Requests, Open Issues, Events This Week, and Important Items</td>
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
                    <tr>
                        <td>Drop table</td>
                        <td>Select a table and use the drop/delete table action</td>
                        <td>Table is removed from the sidebar; data is deleted</td>
                    </tr>
                </tbody>
            </table>

            <h3>Database Management</h3>
            <table className="doc-table">
                <thead><tr><th>Test Case</th><th>Steps</th><th>Expected Result</th></tr></thead>
                <tbody>
                    <tr>
                        <td>Download .db file</td>
                        <td>Click "Download DB" on the Dashboard or Database page</td>
                        <td>Browser downloads a valid <span className="doc-code">.db</span> SQLite file</td>
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
                    <tr>
                        <td>Import & Merge (.db)</td>
                        <td>Click "Import Merge" and upload a <span className="doc-code">.db</span> file</td>
                        <td>Data from the uploaded database is merged into the current database</td>
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
                Current status: <strong>MVP complete</strong> — chat, database browser, and dashboard are functional. Focus is shifting to polish and production readiness.
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

            <h3>Phase 2: Polish & Complete (Next)</h3>
            <div className="doc-callout doc-callout--tip">
                <strong>Goal:</strong> Finish partially-built features so the core experience feels complete and reliable.
            </div>
            <ul>
                <li><strong>Approval Workflow</strong> — Wire up <span className="doc-code">approval_rules</span> and <span className="doc-code">pending_approvals</span> tables end-to-end so users can request changes and admins can approve/reject them</li>
                <li><strong>CSV Import</strong> — Complete the AI-powered column mapping flow for importing spreadsheet data into the correct tables</li>
                <li><strong>Table Creation / Column Addition</strong> — Ensure backend routes match frontend modals for creating new tables and adding columns</li>
                <li><strong>Home Site Setup Wizard</strong> — Guided first-run experience for configuring a new site</li>
                <li><strong>UI/UX Refinements</strong> — Badge text consistency, sidebar user panel polish, loading states, and general fit-and-finish</li>
            </ul>

            <h3>Phase 3: Knowledge & Content</h3>
            <div className="doc-callout doc-callout--tip">
                <strong>Goal:</strong> Users can build and maintain a structured knowledge base alongside their operational data, making the AI assistant more useful over time.
            </div>
            <ul>
                <li><strong>Knowledge Article Management</strong> — Full CRUD UI for <span className="doc-code">knowledge_articles</span> (create, edit, view, delete)</li>
                <li><strong>Tag System UI</strong> — Apply and filter tags across entities (articles, tables, records)</li>
                <li><strong>Workflow Documentation</strong> — Viewer/editor for standard operating procedures and workflows</li>
                <li><strong>Site-Specific Notes</strong> — Miscellaneous knowledge and notes interface for capturing institutional knowledge</li>
            </ul>

            <h3>Phase 4: Production Readiness</h3>
            <div className="doc-callout doc-callout--tip">
                <strong>Goal:</strong> The application is secure, deployable, and suitable for real-world use beyond development.
            </div>
            <ul>
                <li><strong>Authentication & Login</strong> — Replace demo user switching with proper authentication (login page, sessions, password management)</li>
                <li><strong>Environment / Secrets Management</strong> — Remove hardcoded API keys; use environment variables or a secrets manager</li>
                <li><strong>Error Handling & Validation</strong> — Consistent error responses, input validation, and user-facing error messages</li>
                <li><strong>Mobile Responsiveness</strong> — Ensure the UI works well on tablets and phones</li>
                <li><strong>Deployment Pipeline</strong> — Dockerfile, docker-compose, CI/CD configuration</li>
                <li><strong>Security Audit</strong> — CORS lockdown, input sanitization, dependency audit, OWASP review</li>
            </ul>

            <h3>Future Ideas</h3>
            <div className="doc-callout">
                <strong>Goal:</strong> Stretch goals and backlog items to explore once the core product is solid.
            </div>
            <ul>
                <li><strong>Multi-Site Support</strong> — Manage multiple sites from a single instance</li>
                <li><strong>Real-Time Notifications</strong> — WebSocket-based alerts for approvals, report completions, and system events</li>
                <li><strong>Audit Log Viewer</strong> — UI for browsing the audit trail of all data changes</li>
                <li><strong>Advanced Reporting</strong> — Scheduled report customization, custom queries, export options</li>
                <li><strong>Role-Based Access Control</strong> — Granular permissions beyond the current admin/user split</li>
            </ul>
        </section>
    );
}
