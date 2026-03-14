# MileCore

An AI-powered database assistant for IT site operations. MileCore lets support teams manage assets, people, requests, events, inventory, and more through natural language conversation — it translates plain English into database actions automatically.

Built with **FastAPI** + **SQLite** on the backend and **React** + **Vite** on the frontend, powered by **Claude** (Anthropic).

## Features

- **AI Chat Interface** — Ask questions or give instructions in plain English. The AI reads your database schema, generates SQL, and executes it with full audit logging.
- **Streaming Responses** — Real-time token streaming via Server-Sent Events.
- **CSV/XLSX Import** — Upload files through the chat. The AI previews the data, maps columns to the right tables, and bulk-inserts.
- **Query Approval System** — Admins define rules for which write operations need approval. Matching queries are queued for review instead of executing immediately.
- **Email Integration** — Send work-related emails directly from the chat (via Brevo SMTP). The AI looks up recipients in the people table.
- **Database Browser** — Full CRUD UI for all tables: view schemas, browse rows, insert/delete, create/drop tables, add columns, export to XLSX, import from XLSX or `.db` files.
- **Dashboard** — KPI cards and charts (assets, requests, issues, staffing, events). Admin controls for seeding demo data, resetting the database, and triggering daily reports.
- **Daily Reports** — Automated email reports sent to supervisors each morning with new issues, vendor visits, and flagged items.
- **Chat Persistence** — Conversations are saved per user and can be resumed from the sidebar.
- **Audit Logging** — Every INSERT, UPDATE, and DELETE is automatically recorded in the `audit_log` table.
- **User Roles** — Admin users can manage approval rules, review pending queries, and access admin endpoints. Regular users can chat, upload, and browse.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| AI | Anthropic Claude API (claude-sonnet-4-6 default) |
| Database | SQLite (WAL mode, foreign keys enabled) |
| Frontend | React 18, Vite, Recharts, react-markdown |
| Email | Brevo (Sendinblue) SMTP |

## Project Structure

```
milebot/
├── run.py                     # Entry point — DB init, frontend build, server start
├── schema.sql                 # Full database schema (25+ tables, triggers)
├── initial_seed.py            # Bootstrap: default company, site, teams, 2 users
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (not committed)
│
├── backend/
│   ├── app.py                 # FastAPI app factory, CORS, static files, lifespan
│   ├── config.py              # Loads .env — API key, DB path, email config
│   ├── database.py            # SQLite connection, execute/validate, reset/migrate
│   ├── claude_client.py       # Claude integration — streaming, tool execution loop
│   ├── prompts.py             # System prompt template + 7 tool definitions
│   ├── sessions.py            # Chat session CRUD (UUID-based)
│   ├── email_sender.py        # Brevo SMTP wrapper
│   ├── daily_report.py        # Scheduled supervisor reports
│   └── routes/
│       ├── chat.py            # /api/chat/stream, /api/sessions, /api/user
│       ├── dashboard.py       # /api/dashboard/* — KPIs, seed, reset
│       ├── upload.py          # /api/upload/stage — CSV staging for AI import
│       └── database_browser.py# /api/tables/* — CRUD, export, import
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Layout, routing, demo modal, user switching
│   │   ├── chat.jsx           # Chat UI, SSE streaming, file upload, sessions
│   │   ├── browser.jsx        # Database browser — tables, rows, schema
│   │   ├── dashboard.jsx      # KPI cards, charts, admin actions
│   │   ├── documentation.jsx  # In-app help (16 sections)
│   │   └── components.jsx     # Reusable Modal component
│   ├── static/
│   │   ├── css/style.css      # Dark theme, full styling
│   │   └── img/               # Logo, profile pictures
│   ├── index.html
│   ├── vite.config.js         # Dev proxy to :8000, manual chunks
│   └── package.json
│
└── dummy_files/               # Sample data for demo seeding
    ├── demo_full_import.xlsx  # All tables in one workbook (one-click load)
    ├── companies.csv
    ├── sites.csv
    ├── rooms.csv
    ├── people.csv
    ├── assets.csv
    ├── requests.csv
    ├── technical_issues.csv
    ├── events.csv
    └── inventory_items.csv
```

## Getting Started

### Prerequisites

- Python 3.13+
- Node.js 18+ and npm
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# Clone the repo
git clone <repo-url> && cd milebot

# Install Python dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env   # or create manually (see below)
```

### Configuration

Create a `.env` file in the project root:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional — Claude model (default: claude-sonnet-4-6)
CLAUDE_MODEL=claude-sonnet-4-6

# Optional — Database path (default: milecore.db)
DATABASE_PATH=milecore.db

# Optional — Email (Brevo SMTP)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_LOGIN=your-login@smtp-brevo.com
BREVO_SMTP_PASSWORD=your-smtp-password
BREVO_SENDER_EMAIL=noreply@yourdomain.com
BREVO_SENDER_NAME=MileCore

# Optional — Daily report schedule (24-hour, default: 07:00)
DAILY_REPORT_HOUR=7
DAILY_REPORT_MINUTE=0
```

### Running

```bash
python run.py
```

This will:
1. Initialize the SQLite database from `schema.sql` (or migrate if it already exists)
2. Seed the default company, site, teams, and two demo users (Dan = admin, Bob = user)
3. Install frontend npm dependencies (if needed) and build with Vite
4. Start the Uvicorn server on `http://localhost:8000`

### Frontend Development

For hot-reloading during frontend work:

```bash
# Terminal 1 — backend
python run.py

# Terminal 2 — Vite dev server (proxies /api to :8000)
cd frontend && npm run dev
# Access at http://localhost:5173
```

## Database

### Schema

The database has 25+ tables organized into logical groups:

- **Organizations** — `companies`, `sites`, `rooms`
- **People & Teams** — `people`, `teams`, `pto`
- **Assets** — `assets`, `asset_relationships`
- **Support** — `requests`, `technical_issues`, `issue_occurrences`
- **Events** — `events`, `event_participants`, `event_assets`
- **Notes & Work** — `notes`, `work_logs`
- **Inventory** — `inventory_items`, `inventory_stock`, `inventory_transactions`
- **Changes & Contracts** — `changes`, `vendor_contracts`
- **Knowledge** — `knowledge_articles`, `misc_knowledge`, `workflows`, `tags`, `entity_tags`
- **System** — `audit_log`, `app_settings`, `chat_sessions`, `chat_messages`, `approval_rules`, `pending_approvals`

All table definitions use `CREATE TABLE IF NOT EXISTS` for safe re-initialization. Auto-updating `updated_at` triggers are set on key tables.

### Reset & Seed

- **Reset**: Dashboard > "Reset Database" button — drops all tables, recreates schema, re-seeds the two default users.
- **Seed Demo Data**: Demo modal > "click here" — loads `dummy_files/demo_full_import.xlsx` (~80 rows across 9 tables: companies, sites, rooms, people, assets, requests, issues, events, inventory).

### Persistence

The database file (`milecore.db`) persists across restarts. On startup, `run.py` applies the schema idempotently — existing data is preserved.

## AI Tools

The Claude assistant has access to 7 tools:

| Tool | Description |
|------|-------------|
| `execute_sql` | Run any SQL query (SELECT, INSERT, UPDATE, DELETE) |
| `create_table` | Create new tables with custom schemas |
| `send_email` | Send emails via Brevo SMTP |
| `import_csv` | Bulk import from staged CSV files |
| `manage_approval_rules` | Add, list, or remove approval rules (admin only) |
| `submit_for_approval` | Queue a query for admin review |
| `review_approvals` | List, approve, or reject pending queries (admin only) |

The AI receives the full database schema, current user context, home site info, and active approval rules in its system prompt. Prompt caching is used to reduce API costs.

## API Endpoints

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/stream` | Streaming chat (SSE) |
| POST | `/api/chat` | Non-streaming chat |
| GET | `/api/sessions` | List user's sessions |
| GET | `/api/sessions/:id` | Load session history |
| GET | `/api/user` | Current user profile |
| GET | `/api/home-site` | Configured home site |
| GET | `/api/approvals/pending-count` | Pending approval count |

### Database Browser
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tables` | List all tables |
| POST | `/api/tables` | Create table |
| DELETE | `/api/tables/:name` | Drop table |
| GET | `/api/tables/:name/schema` | Column metadata |
| GET | `/api/tables/:name/rows` | Paginated rows |
| POST | `/api/tables/:name/rows` | Insert row |
| DELETE | `/api/tables/:name/rows/:id` | Delete row |
| POST | `/api/tables/:name/columns` | Add column |
| GET | `/api/tables/export` | Export all tables to XLSX |
| GET | `/api/tables/download` | Download raw .db file |
| POST | `/api/tables/import` | Import XLSX (replace) |
| POST | `/api/tables/import-merge` | Import XLSX/DB (merge) |

### Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard/overview` | KPI summary |
| GET | `/api/dashboard/assets-by-period` | Assets created by date |
| GET | `/api/dashboard/issues-summary` | Request/issue breakdown |
| GET | `/api/dashboard/vendor-visits` | Vendor visit stats |
| GET | `/api/dashboard/staff-per-site` | Headcount by site |
| POST | `/api/dashboard/seed-demo` | Load demo data from XLSX |
| POST | `/api/dashboard/reset-database` | Drop and reinitialize DB |

### Upload
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload/stage` | Stage CSV for AI import |

## Demo Users

The app ships with two hardcoded demo users (no authentication):

| User | Role | Person ID | Job Title |
|------|------|-----------|-----------|
| Dan Gocan | Admin | 1 | IT Technician |
| Bob User | User | 2 | AV Technician |

Switch between them using the button in the chat sidebar. The admin user sees the pending approvals badge and has access to approval management tools.

## Credits

- Profile pictures: [JensenArtOfficial on Pixabay](https://pixabay.com/users/jensenartofficial-31380959/)
- Background image: [Pixabay](https://pixabay.com/illustrations/wood-texture-dark-black-wall-1759566/)
