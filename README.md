# MileCore

An AI-powered database assistant for IT site operations. MileCore lets support teams manage assets, people, tickets, events, inventory, and more through natural language conversation — it translates plain English into database actions automatically.

Built with **FastAPI** + **PostgreSQL** on the backend and **React** + **Vite** on the frontend, powered by **Claude** (Anthropic).

## Features

- **AI Chat Interface** — Ask questions or give instructions in plain English. The AI reads your database schema, generates SQL, and executes it with full audit logging.
- **Streaming Responses** — Real-time token streaming via Server-Sent Events.
- **CSV/XLSX Import** — Upload files through the chat. The AI previews the data, maps columns to the right tables, and bulk-inserts.
- **Query Approval System** — Admins define rules for which write operations need approval. Matching queries are queued for review instead of executing immediately.
- **Email Integration** — Send work-related emails directly from the chat (via Brevo SMTP). The AI looks up recipients in the people table.
- **Database Browser** — Full CRUD UI for all tables: view schemas, browse rows, insert/delete, create tables, add columns, export to XLSX, import from XLSX.
- **Dashboard** — KPI cards and charts (assets, tickets, issues, staffing, events). Admin controls for resetting the database and triggering daily reports.
- **Daily Reports** — Automated email reports sent to supervisors each morning with new issues, vendor visits, and flagged items.
- **Chat Persistence** — Conversations are saved per user and can be resumed from the sidebar.
- **Audit Logging** — Every INSERT, UPDATE, and DELETE is automatically recorded in the `audit_log` table.
- **User Roles** — Admin users can manage approval rules, review pending queries, and access admin endpoints. Regular users can chat, upload, and browse.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| AI | Anthropic Claude API (claude-sonnet-4-6 default) |
| Database | PostgreSQL (connection pooling, Row-Level Security) |
| Frontend | React 18, Vite, Recharts, react-markdown |
| Email | Brevo (Sendinblue) SMTP |

## Architecture Diagram

[View interactive architecture diagram on Mermaid Live](https://mermaid.live/edit#pako:eNqNV21v2zYQ_iuEPrWYHLuNncXGUCC2U6xbsrmR2wGbB5WhGFuLRGoklZfW_e97SEqyLLvF_ME6nu6Nzx3vqC8BkwkPJsFa0WJDlvOVIPh90Fy9eGH_SZ9MlXwE9fLlSvi3urz14m-VFIaL5K9VUJOkR244ZYb8QD6mhq-Cv72O_c021EDUPsiCrjlkGeiTf_TTntyc6g3k7ONWUpXUwknNONSYVkE6NUNvqeZ13FC89dShmmTaakhW5lwYalIpGmdt5p4mdnmIBNXmYvHOAuEpMqXs3uLRp0W657TRuZGl4da_I8i1TMqM6z3ZGjUnAUnlVPoOteL5p1vVfxNFl0QbxWmeinVINNcaAevQvSzt_gsl79KMh4QWIB9odujDQt3xsQO7cqQBhQ5txpSpzCc8l_DIkxAZIIprbg5MV1k4sO6TFNepqZyAm3GSCl1wZoEPyeUT4xnhT4VUxnv1nDR3HOs4kY8ikzQ58P2hsOyO69Ixa4ez6CPgo2uAh5L1RvfstLK9l72ZVNaofXw7dRktEz7LUtQRZJlbxsyt6wAu1likjGRSFhXOVTIRj5Ci16yPZM2DCNM1nk1VvL_C6SNMClEB6dj_llw9A0zOSo8uAkoNfB8aj6pCgvG6phrM7AGumGR282F-JLI0e77hFkwXHFaxcssmQLbhFrQEiBZcPaRaKuJFDnG8zGEhQibcAed2FWu3rM1NFX-QJLpeLoiH98DGQsm8MHY7haeaSJ614TnxXGBupMxIwu_098ogWlzAEv6BE4IXa2_KdgtGqMZB0LacEOLTycbk2Xebx3xqbfmMNd2rR3IcWobyOklu90JJUuVzSq5u2i3wd7WGHfxTkX52bUu7qBg2BlanPufTd-JOUWi4J6qsZKZU3NcgQsFZV1LmXa0Fl0VmS84ThKLHLVGg3lfhmCExlhOSwsiO-oXDBuqecEoer9DjhjrJfPCbtOg6j8qiqqmKcvqKo661tWA424iU0SxOtQbPV72jY8lYqRQX7ACIywcUjI3JE06HOxI7QLdLWQoAmwi76n9IdQ_l3yQwc3BYhjMipIPxEesYZ8x3T7E-kokHlwfrUypflsiARVAbye6xMUWFpi7rXeVfhXyEtn3gOK19Au_rVeziz2oo8lSzuHnpQ7vL0IK7QLtDYXF2RNWb7Q5stzLPsV-49mG35q1jwOBcGoPzoHfjJlZl479A_eNtfHwUzaetK4KvXRDx_kxzrBws2gby2Lm6fDJcCZrZzFakP67dEvB92vp1BLHzu0cuhNkoWaTMuV2iLfQwTwltNew9K64HwciuF3nFXerg3zWvY1EveV5AuQ-0i34zknDWnfDuWkZ6vTfbn5fLxdY2Ic-3fcizr6_6v0T9WRRtnfC-WnNfq-25Rm4Vby6jJfoV7hLb3X3Dy9irQSOz3d0UqrfT5pbViLQn_jGpt-hrxE_hbXtEt6PyVyIbcz2Hjr1rz9fqfYvjnEXNNLVJRWfI9LaSams42SbFuMkUcMkb0e-5qCdLE_5BCO-v_FCpvNct_hvibtjtKbTGX52TekjA_XzqmS0p7_ba1ogrxjq0JnlecS-OdtY6r6sq2mWqQtZelHF_QoS2eI9K_Z8UvXOXLr9jJCtp7NVBN3cJJ_7e3mG6KHaFLA4d4D59-hSE-M5Jk2CCYcfDIOcKAlgGX6yVVWA2PMcny4TYO4u6XwUr8RU6aP5_YhLWarhHrjfB5A7dC6uywN2Lz1OKnrMTcT5nshQmmIychWDyJXgKJr3Xo9cn47Ozs9F4NBydj8-HwzB4Bv_V6eDkdHA6GA3PB-PRj4PTr2Hw2Xl9ffLq_HwwOBuejl8Nx8PROAw42q5U1_7TzX3Bff0P_E-HeQ)

## Project Structure

```
milebot/
├── run.py                     # Entry point — DB init, frontend build, server start
├── schema_pg.sql              # Full PostgreSQL database schema (25+ tables, triggers)
├── initial_seed.py            # Bootstrap: default company, site, teams, 2 users
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (not committed)
│
├── backend/
│   ├── app.py                 # FastAPI app factory, CORS, static files, lifespan
│   ├── config.py              # Loads .env — API key, DB path, email config
│   ├── database.py            # PostgreSQL connection pooling, execute/validate, reset/migrate
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
│   │   ├── App.jsx            # Layout, routing, user switching
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

# Optional — Spare API key (automatic failover on rate limit or auth error)
ANTHROPIC_API_KEY_SPARE=sk-ant-...

# Optional — Claude model (default: claude-sonnet-4-6)
CLAUDE_MODEL=claude-sonnet-4-6

# Optional — PostgreSQL connection (default: postgresql://truecore:truecore@localhost:5432/truecore)
DATABASE_URL=postgresql://truecore:truecore@localhost:5432/truecore

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
1. Connect to PostgreSQL and initialize the schema from `schema_pg.sql`
2. Seed the default instance, company, site, teams, and the default users
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
- **Support** — `tickets`, `technical_issues`, `issue_occurrences`
- **Events** — `events`, `event_participants`, `event_assets`
- **Notes & Work** — `notes`, `work_logs`
- **Inventory** — `inventory_items`, `inventory_stock`, `inventory_transactions`
- **Changes & Contracts** — `changes`, `vendor_contracts`
- **Knowledge** — `knowledge_articles`, `misc_knowledge`, `workflows`, `tags`, `entity_tags`
- **System** — `audit_log`, `app_settings`, `chat_sessions`, `chat_messages`, `approval_rules`, `pending_approvals`

All table definitions use `CREATE TABLE IF NOT EXISTS` for safe re-initialization. Auto-updating `updated_at` triggers are set on key tables.

### Reset & Seed

- **Reset**: Dashboard > "Reset Database" button — deletes all tenant-scoped data for the current instance.

### Persistence

PostgreSQL stores all data persistently. On startup, `run.py` applies the schema idempotently — existing data is preserved.

## AI Tools

The Claude assistant has access to 9 tools:

| Tool | Description |
|------|-------------|
| `execute_sql` | Run any SQL query (SELECT, INSERT, UPDATE, DELETE) |
| `create_table` | Create new tables with custom schemas |
| `send_email` | Send emails via Brevo SMTP |
| `import_csv` | Bulk import from staged CSV files |
| `manage_approval_rules` | Add, list, or remove approval rules (admin only) |
| `submit_for_approval` | Queue a query for admin review |
| `review_approvals` | List, approve, or reject pending queries (admin only) |
| `generate_excel` | Generate downloadable .xlsx files from query results |
| `invite_user` | Invite someone to join the instance (owner only) |

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
| GET | `/api/tables/:name/schema` | Column metadata |
| GET | `/api/tables/:name/rows` | Paginated rows |
| POST | `/api/tables/:name/rows` | Insert row |
| DELETE | `/api/tables/:name/rows/:id` | Delete row |
| POST | `/api/tables/:name/columns` | Add column |
| GET | `/api/tables/export` | Export all tables to XLSX |
| POST | `/api/tables/import` | Import XLSX (replace) |
| POST | `/api/tables/import-merge` | Import XLSX (merge) |

### Dashboard
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard/overview` | KPI summary |
| GET | `/api/dashboard/assets-by-period` | Assets created by date |
| GET | `/api/dashboard/issues-summary` | Ticket/issue breakdown |
| GET | `/api/dashboard/vendor-visits` | Vendor visit stats |
| GET | `/api/dashboard/staff-per-site` | Headcount by site |
| POST | `/api/dashboard/reset-database` | Drop and reinitialize DB |

### Upload
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload/stage` | Stage CSV for AI import |

## Credits

- Profile pictures: [JensenArtOfficial on Pixabay](https://pixabay.com/users/jensenartofficial-31380959/)
- Background image: [Pixabay](https://pixabay.com/illustrations/wood-texture-dark-black-wall-1759566/)
