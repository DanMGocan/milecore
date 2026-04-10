# MileCore

**AI-powered operations management platform for IT site teams.**

MileCore lets support teams manage assets, people, tickets, maintenance, projects, and more through natural language conversation. Users type plain English and the AI translates it into database actions automatically, with full audit logging, approval workflows, and multi-tenant isolation.

Built as a full-stack SaaS application with a FastAPI + PostgreSQL backend and a React + Vite frontend.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688)

---

## Table of Contents

- [What It Does](#what-it-does)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Features](#features)
- [Database Schema](#database-schema)
- [AI Tools](#ai-tools)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Credits](#credits)

---

## What It Does

MileCore is an operations management tool designed for IT, facilities, and workplace technology teams. Instead of navigating complex admin panels, users interact with a chat interface powered by Claude (Anthropic). The AI understands the full database schema, generates SQL on the fly, and executes queries with safety checks and audit trails.

**Example interactions:**
- *"Show me all open tickets assigned to the AV team"*
- *"Create an asset for the new Dell monitor in Room 4.01, serial number ABC123"*
- *"How many PTO days has Maria taken this quarter?"*
- *"Email the vendor about the broken projector in the main conference room"*
- *"Generate an Excel report of all assets deployed in the last 30 days"*

The platform supports multi-tenant SaaS deployment with Stripe billing, or self-hosted BYOK (Bring Your Own Key) mode with any major LLM provider.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, psycopg 3 |
| **Frontend** | React 18, Vite, Recharts, react-markdown |
| **Database** | PostgreSQL 15+ with Row-Level Security |
| **AI / LLM** | Anthropic Claude (native SDK), LiteLLM (multi-provider: OpenAI, Google, DeepSeek) |
| **Auth** | JWT access/refresh tokens, bcrypt, Google OAuth 2.0 |
| **Email** | Brevo SMTP (outbound + inbound webhook parsing) |
| **Billing** | Stripe (subscriptions, metered usage, add-ons) |
| **Storage** | S3-compatible object storage (boto3) for file attachments |

---

## Architecture

```
Browser (React SPA)
    |
    | REST + SSE (Server-Sent Events)
    v
FastAPI Application
    |
    |-- Auth Middleware (JWT + instance context)
    |-- Route Handlers (chat, assets, tickets, maintenance, billing, ...)
    |-- Claude Client (LLM orchestration loop)
    |       |
    |       |-- System Prompt Builder (schema DDL + user context + approval rules)
    |       |-- Tool Execution Engine (9 tools: SQL, email, Excel, approvals, ...)
    |       |-- Token Metering + History Trimming
    |       |-- Prompt Caching (reduces API cost on repeated queries)
    |       |
    |       v
    |   Anthropic API / LiteLLM (BYOK)
    |
    |-- PostgreSQL (50+ tables, RLS, audit triggers)
    |-- Brevo SMTP (outbound email, inbound webhook)
    |-- Stripe API (subscriptions, metering)
    |-- S3 (file attachments)
    |
    |-- Background Tasks:
            |-- Daily Report Scheduler (supervisor emails at 07:00 UTC)
            |-- Reminder Processor (checks due reminders every 60s)
            |-- Maintenance Scheduler (generates work orders every 5 min)
```

[View interactive Mermaid diagram](https://mermaid.live/edit#pako:eNqNV21v2zYQ_iuEPrWYHLuNncXGUCC2U6xbsrmR2wGbB5WhGFuLRGoklZfW_e97SEqyLLvF_ME6nu6Nzx3vqC8BkwkPJsFa0WJDlvOVIPh90Fy9eGH_SZ9MlXwE9fLlSvi3urz14m-VFIaL5K9VUJOkR244ZYb8QD6mhq-Cv72O_c021EDUPsiCrjlkGeiTf_TTntyc6g3k7ONWUpXUwknNONSYVkE6NUNvqeZ13FC89dShmmTaakhW5lwYalIpGmdt5p4mdnmIBNXmYvHOAuEpMqXs3uLRp0W657TRuZGl4da_I8i1TMqM6z3ZGjUnAUnlVPoOteL5p1vVfxNFl0QbxWmeinVINNcaAevQvSzt_gsl79KMh4QWIB9odujDQt3xsQO7cqQBhQ5txpSpzCc8l_DIkxAZIIprbg5MV1k4sO6TFNepqZyAm3GSCl1wZoEPyeUT4xnhT4VUxnv1nDR3HOs4kY8ikzQ58P2hsOyO69Ixa4ez6CPgo2uAh5L1RvfstLK9l72ZVNaofXw7dRktEz7LUtQRZJlbxsyt6wAu1likjGRSFhXOVTIRj5Ci16yPZM2DCNM1nk1VvL_C6SNMClEB6dj_llw9A0zOSo8uAkoNfB8aj6pCgvG6phrM7AGumGR282F-JLI0e77hFkwXHFaxcssmQLbhFrQEiBZcPaRaKuJFDnG8zGEhQibcAed2FWu3rM1NFX-QJLpeLoiH98DGQsm8MHY7haeaSJ614TnxXGBupMxIwu_098ogWlzAEv6BE4IXa2_KdgtGqMZB0LacEOLTycbk2Xebx3xqbfmMNd2rR3IcWobyOklu90JJUuVzSq5u2i3wd7WGHfxTkX52bUu7qBg2BlanPufTd-JOUWi4J6qsZKZU3NcgQsFZV1LmXa0Fl0VmS84ThKLHLVGg3lfhmCExlhOSwsiO-oXDBuqecEoer9DjhjrJfPCbtOg6j8qiqqmKcvqKo661tWA424iU0SxOtQbPV72jY8lYqRQX7ACIywcUjI3JE06HOxI7QLdLWQoAmwi76n9IdQ_l3yQwc3BYhjMipIPxEesYZ8x3T7E-kokHlwfrUypflsiARVAbye6xMUWFpi7rXeVfhXyEtn3gOK19Au_rVeziz2oo8lSzuHnpQ7vL0IK7QLtDYXF2RNWb7Q5stzLPsV-49mG35q1jwOBcGoPzoHfjJlZl479A_eNtfHwUzaetK4KvXRDx_kxzrBws2gby2Lm6fDJcCZrZzFakP67dEvB92vp1BLHzu0cuhNkoWaTMuV2iLfQwTwltNew9K64HwciuF3nFXerg3zWvY1EveV5AuQ-0i34zknDWnfDuWkZ6vTfbn5fLxdY2Ic-3fcizr6_6v0T9WRRtnfC-WnNfq-25Rm4Vby6jJfoV7hLb3X3Dy9irQSOz3d0UqrfT5pbViLQn_jGpt-hrxE_hbXtEt6PyVyIbcz2Hjr1rz9fqfYvjnEXNNLVJRWfI9LaSams42SbFuMkUcMkb0e-5qCdLE_5BCO-v_FCpvNct_hvibtjtKbTGX52TekjA_XzqmS0p7_ba1ogrxjq0JnlecS-OdtY6r6sq2mWqQtZelHF_QoS2eI9K_Z8UvXOXLr9jJCtp7NVBN3cJJ_7e3mG6KHaFLA4d4D59-hSE-M5Jk2CCYcfDIOcKAlgGX6yVVWA2PMcny4TYO4u6XwUr8RU6aP5_YhLWarhHrjfB5A7dC6uywN2Lz1OKnrMTcT5nshQmmIychWDyJXgKJr3Xo9cn47Ozs9F4NBydj8-HwzB4Bv_V6eDkdHA6GA3PB-PRj4PTr2Hw2Xl9ffLq_HwwOBuejl8Nx8PROAw42q5U1_7TzX3Bff0P_E-HeQ)

---

## Features

### Natural Language Chat Interface
Users interact with the system by typing plain English. The AI reads the full database schema, understands the request, generates SQL, executes it, and returns a formatted response. Responses stream in real time via Server-Sent Events.

### Multi-Tenant Architecture
Each organization gets its own isolated instance. PostgreSQL Row-Level Security ensures that queries only ever return data belonging to the current tenant. All tenant-scoped tables include an `instance_id` column, and every database call sets a session variable that RLS policies check automatically.

### Authentication and Authorization
- JWT-based auth with access and refresh tokens stored in HTTP-only cookies
- Google OAuth 2.0 support
- Three roles: **owner** (full control, user invitations, billing), **admin** (approval management, reports), and **user** (chat, upload, browse)
- Role-based tool filtering: admin-only and owner-only tools are hidden from unauthorized users

### Approval Workflow
Admins define rules for sensitive operations (e.g., "INSERT INTO pto requires approval"). When a user's request matches a rule, the AI queues the query for review instead of executing it. Admins can then approve or reject from the admin panel. Approved queries execute automatically.

### File Upload and Import
Users can upload CSV or XLSX files through the chat. The AI previews the data, suggests column mappings to the target table, and bulk-inserts after confirmation.

### Email Integration
- **Outbound**: Send emails directly from chat via Brevo SMTP. The AI looks up recipients in the people table.
- **Ticket replies**: Threaded email conversations using Message-ID, In-Reply-To, and References headers.
- **Inbound**: Webhook endpoint receives emails from Brevo and parses them into tickets automatically.
- **Daily reports**: Scheduled supervisor emails each morning with new issues, vendor visits, and flagged items.
- **Reminders**: Create one-time, daily, weekly, or monthly email reminders through chat.

### Database Browser
A full CRUD interface for all tables, accessible outside of chat:
- View table schemas (columns, types, constraints)
- Browse rows with pagination
- Insert and delete records
- Create new tables and add columns
- Export all tables to XLSX
- Import from XLSX (merge or replace mode)

### Dashboard
KPI cards and charts covering assets, tickets, issues, staffing, and events. Admin controls for resetting the database, seeding sample data, and manually triggering daily reports.

### Asset Lifecycle Management
- Full asset CRUD with assignment tracking and status history
- Enforced state machine for lifecycle transitions (e.g., active to deployed, in_repair, decommissioned)
- Asset relationships (connected_to, part_of, bundled_with, replaced_by)
- Software installation and license tracking
- Disposal records

### Maintenance and Inspections
- Maintenance plans (preventive, predictive, corrective) with configurable recurrence
- Automatic work order generation: a background scheduler checks due plans every 5 minutes
- Inspection templates with checklists (pass/fail, numeric, text, photo items)
- Overdue tracking and priority management

### Project Management
Projects with members, tasks, updates, and expense tracking. Linked to the broader operational context so the AI can cross-reference project work with assets, tickets, and people.

### Booking System
Reserve rooms, desks, parking spaces, lockers, or assets. Conflict detection prevents double-booking. Automatic AV team notifications for rooms with AV equipment or large capacity.

### Service Catalog and Request Fulfillment
Define a catalog of available services with approval requirements. Users submit service requests through structured templates. Each request generates trackable fulfillment tasks that can link to tickets or work orders.

### Billing (SaaS Mode)
- Query-based tiers via Stripe (250 queries per tier at EUR 24.99)
- Per-seat pricing for BYOK instances (EUR 9.99/user/month)
- Add-on modules: email integration, daily reports, inbound email parsing, bookings
- Token metering: every API call logged with input/output/cache token counts

### LLM Provider Flexibility
- **SaaS mode**: Native Anthropic SDK with prompt caching
- **BYOK mode**: LiteLLM abstraction supporting Anthropic, OpenAI, Google, and DeepSeek
- Encrypted API key storage for customer-provided keys
- Automatic tool format conversion between Anthropic and OpenAI schemas

### Audit Logging
Every INSERT, UPDATE, and DELETE is recorded in the `audit_log` table with the entity type, entity ID, action, changed data, and timestamp. The audit log is read-only and cannot be modified through the AI.

### Token Optimization
- Prompt caching on system blocks (schema, instructions) to reduce API costs
- Smart history trimming: keeps the last 20 messages while preserving tool_use/tool_result pairs
- Tool result truncation at 32KB to prevent token explosion from large query results
- Token metering threshold: 80,000 tokens counts as 1 billable query

---

## Database Schema

The PostgreSQL schema contains 50+ tables organized into these groups:

| Group | Tables |
|-------|--------|
| **Global (no RLS)** | `auth_users`, `instances`, `instance_memberships`, `instance_invitations` |
| **Organizations** | `companies`, `sites`, `floors`, `zones`, `rooms`, `desks`, `parking_spaces`, `lockers` |
| **People and Teams** | `people`, `teams`, `pto` |
| **Assets** | `assets`, `asset_assignments`, `asset_status_history`, `asset_relationships`, `licenses`, `software_installations`, `disposal_records` |
| **Tickets** | `tickets`, `ticket_replies`, `ticket_watchers`, `ticket_attachments`, `ticket_timeline` |
| **Issues** | `technical_issues`, `issue_occurrences` |
| **Events** | `events`, `event_participants`, `event_assets` |
| **Projects** | `projects`, `project_members`, `project_tasks`, `project_updates`, `project_expenses` |
| **Work and Notes** | `work_logs`, `notes` |
| **Inventory** | `inventory_items`, `inventory_stock`, `inventory_transactions` |
| **Maintenance** | `maintenance_tasks`, `maintenance_plans`, `work_orders`, `inspections`, `inspection_records`, `checklist_templates`, `checklist_template_items`, `checklist_responses` |
| **Services** | `service_catalog`, `service_request_templates`, `service_requests`, `request_fulfillment_tasks`, `service_request_task_progress` |
| **Changes and Contracts** | `changes`, `vendor_contracts` |
| **Knowledge** | `knowledge_articles`, `workflows`, `misc_knowledge`, `tags`, `entity_tags` |
| **System** | `audit_log`, `app_settings`, `chat_sessions`, `chat_messages`, `approval_rules`, `pending_approvals`, `reminders`, `query_token_log`, `bookings`, `subscription_events` |

All tenant-scoped tables use `CREATE TABLE IF NOT EXISTS` for safe re-initialization. Auto-updating `updated_at` triggers are set on key tables.

---

## AI Tools

The Claude assistant has access to these tools during conversation:

| Tool | What It Does |
|------|-------------|
| `execute_sql` | Run SELECT, INSERT, UPDATE, or DELETE queries against the database |
| `create_table` | Create new tables with custom schemas |
| `send_email` | Send emails via Brevo SMTP after looking up recipients |
| `reply_to_ticket` | Send threaded ticket replies with proper email headers |
| `generate_excel` | Create downloadable .xlsx files from query results (multi-sheet) |
| `import_csv` | Bulk import from staged CSV files with column mapping |
| `manage_approval_rules` | Add, list, or remove approval rules (admin only) |
| `submit_for_approval` | Queue a write query for admin review |
| `review_approvals` | List, approve, or reject pending queries (admin only) |
| `manage_reminders` | Create, list, or cancel scheduled email reminders |
| `invite_user` | Send an invitation email to join the instance (owner only) |

The AI receives the full database schema DDL, current user context, home site info, and active approval rules in its system prompt. Prompt caching keeps costs low on repeated interactions.

---

## API Endpoints

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/stream` | Streaming chat via SSE |
| POST | `/api/chat` | Non-streaming chat |
| GET | `/api/sessions` | List user sessions |
| GET | `/api/sessions/:id` | Load session history |
| GET | `/api/user` | Current user profile |
| GET | `/api/home-site` | Configured home site |
| GET | `/api/approvals/pending-count` | Pending approval count |

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Create account |
| POST | `/api/auth/login` | Login (returns JWT cookies) |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/google` | Google OAuth login |
| POST | `/api/instances/select` | Select active instance |

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

### Inbound Email
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/inbound-email` | Brevo webhook for incoming emails |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 15+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# Clone the repo
git clone <repo-url> && cd milecore

# Install Python dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env
```

### Configuration

Create a `.env` file in the project root:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Required for auth
JWT_SECRET=your-secret-key

# PostgreSQL (default shown)
DATABASE_URL=postgresql://truecore:truecore@localhost:5432/truecore

# Optional - Spare API key (automatic failover on rate limit or auth error)
ANTHROPIC_API_KEY_SPARE=sk-ant-...

# Optional - Claude model (default: claude-sonnet-4-6)
CLAUDE_MODEL=claude-sonnet-4-6

# Optional - Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...

# Optional - Email (Brevo SMTP)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_LOGIN=your-login@smtp-brevo.com
BREVO_SMTP_PASSWORD=your-smtp-password
BREVO_SENDER_EMAIL=noreply@yourdomain.com
BREVO_SENDER_NAME=MileCore

# Optional - Stripe billing
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional - S3 file storage
S3_ENDPOINT_URL=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET_NAME=...

# Optional - BYOK encryption
KEY_ENCRYPTION_KEY=...

# Optional - Daily report schedule (24-hour UTC, default: 07:00)
DAILY_REPORT_HOUR=7
DAILY_REPORT_MINUTE=0
```

### Running

```bash
python run.py
```

This will:
1. Connect to PostgreSQL and apply the schema from `schema_pg.sql` (idempotent)
2. Seed the default instance, company, site, teams, and test users
3. Install frontend npm dependencies (if needed) and build with Vite
4. Start the Uvicorn server on `http://localhost:8000`

### Frontend Development

For hot-reloading during frontend work:

```bash
# Terminal 1 - backend
python run.py

# Terminal 2 - Vite dev server (proxies /api to :8000)
cd frontend && npm run dev
# Access at http://localhost:5173
```

---

## Project Structure

```
milecore/
├── run.py                          # Entry point: DB init, frontend build, server start
├── schema_pg.sql                   # Full PostgreSQL schema (50+ tables, triggers, RLS)
├── initial_seed.py                 # Bootstrap: default instance, company, site, teams, users
├── requirements.txt                # Python dependencies
├── .env                            # Configuration (not committed)
│
├── backend/
│   ├── app.py                      # FastAPI app factory, CORS, lifespan hooks, route registration
│   ├── config.py                   # Environment variable loader
│   ├── auth.py                     # JWT auth, password hashing, InstanceContext dependency
│   ├── database.py                 # Connection pooling, query execution, audit logging, RLS
│   ├── claude_client.py            # LLM chat loop, tool execution, token metering, history trimming
│   ├── llm_client.py               # LLM provider abstraction (Anthropic native / LiteLLM BYOK)
│   ├── prompts.py                  # System prompt template, tool definitions, context builders
│   ├── sessions.py                 # Chat session CRUD
│   ├── email_sender.py             # Brevo SMTP wrapper
│   ├── daily_report.py             # Scheduled supervisor reports
│   ├── reminders.py                # Email reminder scheduling and processing
│   ├── maintenance_scheduler.py    # Work order and inspection auto-generation
│   ├── stripe_billing.py           # Subscription management, metering, add-ons
│   └── routes/
│       ├── chat.py                 # /api/chat/stream, /api/sessions, /api/user
│       ├── auth_routes.py          # /api/auth/signup, login, refresh, Google OAuth
│       ├── dashboard.py            # /api/dashboard/* - KPIs, seed, reset
│       ├── upload.py               # /api/upload/stage - CSV staging
│       ├── database_browser.py     # /api/tables/* - CRUD, export, import
│       ├── asset_routes.py         # Asset lifecycle, assignments, software, disposal
│       ├── maintenance_routes.py   # Plans, work orders, inspections, checklists
│       └── ...                     # Additional route modules
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Layout, routing, navigation
│   │   ├── AuthContext.jsx         # Global auth state, instance selection, token refresh
│   │   ├── auth.jsx                # Login/signup forms, OAuth handling
│   │   ├── chat.jsx                # Chat UI, SSE streaming, file upload, session sidebar
│   │   ├── browser.jsx             # Database browser: tables, rows, schema editor
│   │   ├── dashboard.jsx           # KPI cards, charts, admin actions
│   │   ├── admin.jsx               # Approval queue, user management, billing settings
│   │   ├── billing.jsx             # Subscription management, usage tracking
│   │   ├── landing.jsx             # Home page, instance selector
│   │   ├── documentation.jsx       # In-app help (16 sections)
│   │   └── components.jsx          # Shared UI components
│   ├── static/
│   │   ├── css/style.css           # Dark theme styling
│   │   └── img/                    # Logo, profile pictures
│   ├── index.html
│   ├── vite.config.js              # Dev proxy to :8000, manual chunks
│   └── package.json
```

---

## Design Decisions

**Row-Level Security for tenant isolation**: Every tenant-scoped query sets a PostgreSQL session variable. RLS policies filter rows automatically, making data leaks between tenants impossible at the database level.

**Prompt caching**: The system prompt (which includes the full schema DDL) is cached at the Anthropic API layer. This significantly reduces token costs for repeated interactions within the same session.

**Smart history trimming**: The chat loop keeps the last 20 messages but never breaks tool_use/tool_result pairs. Orphaned tool blocks at the start of the window are skipped to maintain coherent context.

**Tool result truncation**: Large query results are capped at 32KB before being sent back to the LLM. This prevents token explosion while still giving the AI enough data to generate useful responses.

**Asset lifecycle state machine**: Valid status transitions are enforced in code (e.g., "active" can move to "deployed" or "in_repair" but not directly to "disposed"). Every transition is logged in `asset_status_history`.

**Email threading**: Ticket replies include proper Message-ID, In-Reply-To, and References headers so email clients group conversations into threads automatically.

---

## Credits

- Profile pictures: [JensenArtOfficial on Pixabay](https://pixabay.com/users/jensenartofficial-31380959/)
- Background image: [Pixabay](https://pixabay.com/illustrations/wood-texture-dark-black-wall-1759566/)
