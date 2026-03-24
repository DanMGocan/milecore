-- TrueCore.cloud Multi-Tenant SaaS — PostgreSQL Schema
-- Multi-tenant PostgreSQL schema
-- All tenant-scoped tables include instance_id with RLS enforcement

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ============================================================
-- 1. GLOBAL TABLES (no instance_id)
-- ============================================================

CREATE TABLE auth_users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    google_id TEXT UNIQUE,
    display_name TEXT NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE instances (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    tier TEXT DEFAULT 'free',
    status TEXT DEFAULT 'active',
    query_count INTEGER DEFAULT 0,
    query_limit INTEGER DEFAULT 60,
    email_addon BOOLEAN DEFAULT FALSE,
    inbound_email_addon BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_subscription_id TEXT,
    billing_owner_id BIGINT REFERENCES auth_users(id),
    daily_reports_addon BOOLEAN NOT NULL DEFAULT FALSE,
    bookings_addon BOOLEAN NOT NULL DEFAULT FALSE,
    query_pool_reset_at TIMESTAMPTZ,
    email_signature TEXT,
    deployment_mode TEXT NOT NULL DEFAULT 'saas'
        CHECK (deployment_mode IN ('saas', 'byok')),
    llm_provider TEXT DEFAULT 'anthropic'
        CHECK (llm_provider IN ('anthropic', 'openai', 'google', 'deepseek')),
    llm_model TEXT,
    llm_api_key_encrypted BYTEA,
    llm_api_key_iv BYTEA,
    llm_key_last_validated TIMESTAMPTZ,
    query_tier INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE instance_memberships (
    id BIGSERIAL PRIMARY KEY,
    auth_user_id BIGINT NOT NULL REFERENCES auth_users(id),
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    role TEXT DEFAULT 'user',
    person_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(auth_user_id, instance_id)
);

CREATE TABLE instance_invitations (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    email TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    invited_by_auth_user_id BIGINT REFERENCES auth_users(id),
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    UNIQUE(instance_id, email)
);

-- ============================================================
-- 2. TENANT-SCOPED TABLES (all have instance_id)
--    Ordered by FK dependency
-- ============================================================

-- Organizations
CREATE TABLE companies (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    category TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    address TEXT,
    notes TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Core Infrastructure
CREATE TABLE sites (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    client_id INTEGER,
    address TEXT,
    city TEXT,
    country TEXT,
    timezone TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (client_id) REFERENCES companies(id)
);

CREATE TABLE floors (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    level_number INTEGER,
    description TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

CREATE TABLE zones (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    floor_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    zone_type TEXT DEFAULT 'general',
    description TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (floor_id) REFERENCES floors(id)
);

CREATE TABLE rooms (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER NOT NULL,
    floor_id INTEGER,
    zone_id INTEGER,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    capacity INTEGER,
    location TEXT,
    has_av BOOLEAN NOT NULL DEFAULT FALSE,
    features TEXT,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (floor_id) REFERENCES floors(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

CREATE TABLE desks (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER NOT NULL,
    floor_id INTEGER,
    zone_id INTEGER,
    name TEXT NOT NULL,
    code TEXT,
    location TEXT,
    has_monitor BOOLEAN NOT NULL DEFAULT FALSE,
    has_docking_station BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (floor_id) REFERENCES floors(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

CREATE TABLE parking_spaces (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER NOT NULL,
    floor_id INTEGER,
    zone_id INTEGER,
    name TEXT NOT NULL,
    code TEXT,
    location TEXT,
    space_type TEXT DEFAULT 'standard',
    status TEXT DEFAULT 'active',
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (floor_id) REFERENCES floors(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

CREATE TABLE lockers (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER NOT NULL,
    floor_id INTEGER,
    zone_id INTEGER,
    name TEXT NOT NULL,
    code TEXT,
    location TEXT,
    locker_size TEXT DEFAULT 'standard',
    status TEXT DEFAULT 'active',
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (floor_id) REFERENCES floors(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

-- People & Teams
CREATE TABLE teams (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    description TEXT,
    team_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE people (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    role_title TEXT,
    department TEXT,
    site_id INTEGER,
    team_id INTEGER,
    team_role TEXT,
    employer_id INTEGER,
    client_id INTEGER,
    vendor_id INTEGER,
    is_supervisor BOOLEAN NOT NULL DEFAULT FALSE,
    hire_date DATE,
    is_user BOOLEAN NOT NULL DEFAULT FALSE,
    username TEXT,
    user_role TEXT DEFAULT 'user',
    motto TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (employer_id) REFERENCES companies(id),
    FOREIGN KEY (client_id) REFERENCES companies(id),
    FOREIGN KEY (vendor_id) REFERENCES companies(id)
);

-- PTO / Leave
CREATE TABLE pto (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    person_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    leave_type TEXT NOT NULL DEFAULT 'pto',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (person_id) REFERENCES people(id)
);

-- Assets
CREATE TABLE assets (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    asset_tag TEXT,
    serial_number TEXT,
    hostname TEXT,
    asset_type TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    category TEXT,
    operating_system TEXT,
    purchase_date DATE,
    purchase_cost NUMERIC(12,2),
    warranty_expiry DATE,
    warranty_type TEXT CHECK (warranty_type IN ('manufacturer', 'extended', 'third_party')),
    lifecycle_status TEXT DEFAULT 'active',
    ownership_type TEXT,
    vendor_id INTEGER,
    site_id INTEGER,
    room_id INTEGER,
    assigned_to_person_id INTEGER,
    ip_address TEXT,
    mac_address TEXT,
    criticality TEXT DEFAULT 'low' CHECK (criticality IN ('low', 'medium', 'high', 'critical')),
    replacement_due_date DATE,
    notes TEXT,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (vendor_id) REFERENCES companies(id),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (assigned_to_person_id) REFERENCES people(id)
);

CREATE TABLE asset_relationships (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    parent_asset_id INTEGER NOT NULL,
    child_asset_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (parent_asset_id) REFERENCES assets(id),
    FOREIGN KEY (child_asset_id) REFERENCES assets(id)
);

-- Asset lifecycle & tracking
CREATE TABLE asset_status_history (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    asset_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by_person_id INTEGER,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by_person_id) REFERENCES people(id)
);
CREATE INDEX idx_asset_status_history_asset ON asset_status_history(asset_id, created_at);

CREATE TABLE asset_assignments (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    asset_id INTEGER NOT NULL,
    assigned_to_person_id INTEGER NOT NULL,
    assigned_by_person_id INTEGER,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to_person_id) REFERENCES people(id),
    FOREIGN KEY (assigned_by_person_id) REFERENCES people(id)
);
CREATE INDEX idx_asset_assignments_asset ON asset_assignments(asset_id, start_date);

CREATE TABLE licenses (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    vendor_id INTEGER,
    license_key TEXT,
    license_type TEXT NOT NULL DEFAULT 'perpetual'
        CHECK (license_type IN ('perpetual', 'subscription', 'oem', 'volume', 'site', 'open_source')),
    seat_count INTEGER,
    seats_used INTEGER DEFAULT 0,
    cost NUMERIC(12,2),
    cost_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    purchase_date DATE,
    expiry_date DATE,
    notes TEXT,
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'expired', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (vendor_id) REFERENCES companies(id)
);

CREATE TABLE software_installations (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    asset_id INTEGER NOT NULL,
    software_name TEXT NOT NULL,
    version TEXT,
    license_id INTEGER,
    installed_date DATE DEFAULT CURRENT_DATE,
    installed_by_person_id INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (license_id) REFERENCES licenses(id),
    FOREIGN KEY (installed_by_person_id) REFERENCES people(id)
);

CREATE TABLE asset_documents (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    asset_id INTEGER NOT NULL,
    document_name TEXT NOT NULL,
    document_type TEXT DEFAULT 'general'
        CHECK (document_type IN ('warranty', 'invoice', 'manual', 'certificate', 'photo', 'general')),
    s3_key TEXT NOT NULL,
    content_type TEXT,
    file_size_bytes INTEGER,
    uploaded_by_person_id INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by_person_id) REFERENCES people(id)
);

CREATE TABLE disposal_records (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    asset_id INTEGER NOT NULL,
    disposal_method TEXT NOT NULL
        CHECK (disposal_method IN ('recycled', 'donated', 'sold', 'destroyed', 'returned_to_vendor', 'other')),
    disposal_date DATE NOT NULL DEFAULT CURRENT_DATE,
    authorized_by_person_id INTEGER,
    performed_by_person_id INTEGER,
    certificate_reference TEXT,
    proceeds NUMERIC(12,2),
    proceeds_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    data_wiped BOOLEAN NOT NULL DEFAULT FALSE,
    data_wipe_method TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (authorized_by_person_id) REFERENCES people(id),
    FOREIGN KEY (performed_by_person_id) REFERENCES people(id)
);

-- Support & Issues
CREATE TABLE tickets (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    ticket_number TEXT,
    requester_person_id INTEGER,
    site_id INTEGER,
    room_id INTEGER,
    asset_id INTEGER,
    ticket_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    source TEXT,
    assigned_team_id INTEGER,
    assigned_person_id INTEGER,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    due_date DATE,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    email_thread_id TEXT,
    keywords TEXT,
    FOREIGN KEY (requester_person_id) REFERENCES people(id),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE TABLE ticket_replies (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    ticket_id INTEGER NOT NULL,
    reply_body TEXT NOT NULL,
    reply_by_person_id INTEGER,
    reply_to_email TEXT,
    direction TEXT NOT NULL DEFAULT 'outbound',
    email_message_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (reply_by_person_id) REFERENCES people(id)
);

CREATE TABLE ticket_watchers (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    ticket_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    added_by_person_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (person_id) REFERENCES people(id),
    FOREIGN KEY (added_by_person_id) REFERENCES people(id),
    UNIQUE(ticket_id, person_id)
);

CREATE TABLE ticket_attachments (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    ticket_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    uploaded_by_person_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (uploaded_by_person_id) REFERENCES people(id)
);

CREATE TABLE ticket_timeline (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    ticket_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_person_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    detail TEXT,
    related_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (actor_person_id) REFERENCES people(id)
);
CREATE INDEX idx_ticket_timeline_ticket ON ticket_timeline(ticket_id, created_at);

CREATE TABLE technical_issues (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    ticket_id INTEGER,
    asset_id INTEGER,
    site_id INTEGER,
    room_id INTEGER,
    issue_type TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    model TEXT,
    title TEXT NOT NULL,
    symptom TEXT NOT NULL,
    root_cause TEXT,
    resolution TEXT,
    workaround TEXT,
    severity TEXT DEFAULT 'medium',
    recurrence_status TEXT,
    known_issue BOOLEAN NOT NULL DEFAULT FALSE,
    knowledgeworthy BOOLEAN NOT NULL DEFAULT TRUE,
    reported_by_person_id INTEGER,
    resolved_by_person_id INTEGER,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE issue_occurrences (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    technical_issue_id INTEGER NOT NULL,
    asset_id INTEGER,
    ticket_id INTEGER,
    site_id INTEGER,
    room_id INTEGER,
    observed_by_person_id INTEGER,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    outcome TEXT,
    FOREIGN KEY (technical_issue_id) REFERENCES technical_issues(id)
);

-- Events & Activities
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER,
    room_id INTEGER,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    status TEXT DEFAULT 'planned',
    owner_person_id INTEGER,
    related_ticket_id INTEGER,
    impact_level TEXT,
    needs_support BOOLEAN NOT NULL DEFAULT FALSE,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE event_participants (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    event_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    participant_role TEXT,
    attendance_status TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);

CREATE TABLE event_assets (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    event_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    usage_role TEXT,
    notes TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

-- Notes & Work
CREATE TABLE notes (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    note_type TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    site_id INTEGER,
    room_id INTEGER,
    asset_id INTEGER,
    ticket_id INTEGER,
    technical_issue_id INTEGER,
    event_id INTEGER,
    project_id INTEGER,
    project_task_id INTEGER,
    created_by_person_id INTEGER,
    visibility TEXT DEFAULT 'internal',
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE work_logs (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    ticket_id INTEGER,
    technical_issue_id INTEGER,
    event_id INTEGER,
    asset_id INTEGER,
    project_id INTEGER,
    project_task_id INTEGER,
    person_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    time_spent_minutes INTEGER,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Inventory
CREATE TABLE inventory_items (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    sku TEXT,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    unit_of_measure TEXT DEFAULT 'each',
    reorder_threshold INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE inventory_stock (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    inventory_item_id INTEGER NOT NULL,
    site_id INTEGER NOT NULL,
    room_id INTEGER,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id),
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

CREATE TABLE inventory_transactions (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    inventory_item_id INTEGER NOT NULL,
    site_id INTEGER,
    room_id INTEGER,
    transaction_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    related_person_id INTEGER,
    related_ticket_id INTEGER,
    performed_by_person_id INTEGER,
    notes TEXT,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id)
);

-- Changes & Contracts
CREATE TABLE changes (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER,
    room_id INTEGER,
    asset_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    change_type TEXT NOT NULL,
    risk_level TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'planned',
    requested_by_person_id INTEGER,
    implemented_by_person_id INTEGER,
    planned_start TIMESTAMPTZ,
    planned_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    rollback_plan TEXT,
    outcome TEXT,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE vendor_contracts (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    company_id INTEGER NOT NULL,
    site_id INTEGER,
    contract_name TEXT NOT NULL,
    contract_type TEXT,
    start_date DATE,
    end_date DATE,
    sla_description TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    site_id BIGINT REFERENCES sites(id),
    owner_person_id BIGINT REFERENCES people(id),
    status VARCHAR(20) NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned','active','on_hold','completed','cancelled')),
    priority VARCHAR(10) NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    category VARCHAR(20) NOT NULL DEFAULT 'other'
        CHECK (category IN ('infrastructure','operations','maintenance','deployment','migration','other')),
    budget_estimated NUMERIC(12,2),
    budget_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    planned_start DATE,
    planned_end DATE,
    actual_start DATE,
    actual_end DATE,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_members (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    person_id BIGINT NOT NULL REFERENCES people(id),
    role VARCHAR(20) NOT NULL DEFAULT 'contributor'
        CHECK (role IN ('manager','contributor','stakeholder','observer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, person_id)
);

CREATE TABLE IF NOT EXISTS project_tasks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_task_id BIGINT REFERENCES project_tasks(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assigned_person_id BIGINT REFERENCES people(id),
    status VARCHAR(20) NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo','in_progress','done','blocked','cancelled')),
    priority VARCHAR(10) NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    due_date DATE,
    completed_at TIMESTAMPTZ,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_updates (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_person_id BIGINT REFERENCES people(id),
    content TEXT NOT NULL,
    update_type VARCHAR(20) NOT NULL DEFAULT 'general'
        CHECK (update_type IN ('progress','blocker','decision','milestone','general')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_expenses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    description VARCHAR(255) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    category VARCHAR(20) NOT NULL DEFAULT 'other'
        CHECK (category IN ('hardware','software','services','labor','travel','other')),
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    approved_by_person_id BIGINT REFERENCES people(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_links (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, entity_type, entity_id)
);

-- Add project FK constraints to notes and work_logs
ALTER TABLE notes ADD CONSTRAINT fk_notes_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE notes ADD CONSTRAINT fk_notes_project_task FOREIGN KEY (project_task_id) REFERENCES project_tasks(id) ON DELETE SET NULL;
ALTER TABLE work_logs ADD CONSTRAINT fk_work_logs_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE work_logs ADD CONSTRAINT fk_work_logs_project_task FOREIGN KEY (project_task_id) REFERENCES project_tasks(id) ON DELETE SET NULL;

-- Knowledge & Metadata
CREATE TABLE misc_knowledge (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    people_involved TEXT,
    effective_date DATE,
    expiry_date DATE,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

CREATE TABLE knowledge_articles (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    article_type TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    model TEXT,
    asset_type TEXT,
    site_id INTEGER,
    room_id INTEGER,
    created_by_person_id INTEGER,
    approved_by_person_id INTEGER,
    status TEXT DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workflows (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    keywords TEXT,
    contact_person_id INTEGER,
    added_by_person_id INTEGER,
    site_id INTEGER,
    status TEXT DEFAULT 'published',
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (contact_person_id) REFERENCES people(id),
    FOREIGN KEY (added_by_person_id) REFERENCES people(id),
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

CREATE TABLE tags (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL
);

CREATE TABLE entity_tags (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    tag_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    changed_by_person_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE app_settings (
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (instance_id, key)
);

-- Chat Persistence
CREATE TABLE chat_sessions (
    id TEXT NOT NULL,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    person_id INTEGER,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);

CREATE TABLE chat_messages (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

-- Query Approval System
CREATE TABLE approval_rules (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    description TEXT NOT NULL,
    created_by_person_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (created_by_person_id) REFERENCES people(id)
);

CREATE TABLE pending_approvals (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    sql_statement TEXT NOT NULL,
    explanation TEXT NOT NULL,
    matched_rule_id INTEGER,
    matched_rule_description TEXT,
    submitted_by_person_id INTEGER,
    status TEXT DEFAULT 'pending',
    reviewed_by_person_id INTEGER,
    review_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    FOREIGN KEY (matched_rule_id) REFERENCES approval_rules(id),
    FOREIGN KEY (submitted_by_person_id) REFERENCES people(id),
    FOREIGN KEY (reviewed_by_person_id) REFERENCES people(id)
);

-- Billing
CREATE TABLE query_pack_purchases (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    purchased_by_auth_user_id BIGINT NOT NULL REFERENCES auth_users(id),
    queries_added INTEGER NOT NULL DEFAULT 250,
    stripe_payment_intent_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE subscription_events (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    event_type TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Reminders
CREATE TABLE reminders (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    title TEXT NOT NULL,
    message TEXT,
    remind_at TIMESTAMPTZ NOT NULL,
    recurrence TEXT DEFAULT 'one_time'
        CHECK (recurrence IN ('one_time', 'daily', 'weekly', 'monthly')),
    status TEXT DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'completed', 'cancelled')),
    notify_email TEXT NOT NULL,
    notify_person_id INTEGER REFERENCES people(id),
    created_by_person_id INTEGER REFERENCES people(id),
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Inbound Email Routing
CREATE TABLE inbound_email_senders (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    pattern TEXT NOT NULL,
    pattern_type TEXT NOT NULL DEFAULT 'domain',
    added_by_auth_user_id BIGINT REFERENCES auth_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, pattern)
);
CREATE INDEX idx_inbound_senders_instance ON inbound_email_senders(instance_id);

CREATE TABLE inbound_emails (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT REFERENCES instances(id),
    sender_email TEXT NOT NULL,
    sender_name TEXT,
    subject TEXT,
    body_plain TEXT,
    from_domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    ticket_id BIGINT,
    error_message TEXT,
    brevo_message_id TEXT,
    received_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_inbound_emails_instance ON inbound_emails(instance_id);

-- Bookings & Reservations
CREATE TABLE bookings (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    resource_type TEXT NOT NULL,
    resource_id INTEGER NOT NULL,
    site_id INTEGER NOT NULL,
    booked_by_person_id INTEGER NOT NULL,
    title TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'confirmed',
    source TEXT DEFAULT 'chat',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (booked_by_person_id) REFERENCES people(id),
    CHECK (end_time > start_time),
    CHECK (resource_type IN ('room', 'desk', 'parking_space', 'locker', 'asset'))
);

ALTER TABLE bookings ADD CONSTRAINT no_overlapping_bookings
    EXCLUDE USING gist (
        instance_id WITH =,
        resource_type WITH =,
        resource_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status = 'confirmed');

-- Preventive Maintenance & Inspections
-- maintenance_tasks — reusable maintenance activity definitions
CREATE TABLE maintenance_tasks (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'general'
        CHECK (category IN ('hvac','electrical','plumbing','fire_safety','elevator',
                            'cleaning','it_infrastructure','av_equipment','security',
                            'structural','landscaping','general')),
    estimated_duration_minutes INTEGER,
    required_skills TEXT,
    required_tools TEXT,
    instructions TEXT,
    safety_notes TEXT,
    vendor_id INTEGER,
    estimated_cost NUMERIC(10,2),
    cost_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    asset_type_filter TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_person_id INTEGER,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (vendor_id) REFERENCES companies(id),
    FOREIGN KEY (created_by_person_id) REFERENCES people(id)
);

-- checklist_templates — reusable checklist definitions
CREATE TABLE checklist_templates (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    description TEXT,
    checklist_type TEXT NOT NULL DEFAULT 'maintenance'
        CHECK (checklist_type IN ('maintenance','inspection','safety','audit','commissioning','decommission')),
    category TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_person_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (created_by_person_id) REFERENCES people(id)
);

-- checklist_template_items — individual items within a checklist template
CREATE TABLE checklist_template_items (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    checklist_template_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    item_text TEXT NOT NULL,
    item_type TEXT NOT NULL DEFAULT 'pass_fail'
        CHECK (item_type IN ('pass_fail','yes_no','numeric','text','photo','rating')),
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    numeric_min NUMERIC(10,2),
    numeric_max NUMERIC(10,2),
    numeric_unit TEXT,
    help_text TEXT,
    failure_creates_ticket BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id) ON DELETE CASCADE
);

-- maintenance_plans — scheduled groups of tasks with recurrence
CREATE TABLE maintenance_plans (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    description TEXT,
    plan_type TEXT NOT NULL DEFAULT 'preventive'
        CHECK (plan_type IN ('preventive','predictive','corrective','condition_based')),
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    recurrence TEXT NOT NULL DEFAULT 'monthly'
        CHECK (recurrence IN ('daily','weekly','biweekly','monthly','quarterly',
                              'semi_annual','annual','custom')),
    custom_interval_days INTEGER,
    start_date DATE NOT NULL,
    end_date DATE,
    next_due_date DATE NOT NULL,
    last_generated_at TIMESTAMPTZ,
    lead_time_days INTEGER NOT NULL DEFAULT 3,
    seasonal_months TEXT,
    exclude_weekends BOOLEAN NOT NULL DEFAULT TRUE,
    site_id INTEGER,
    room_id INTEGER,
    asset_id INTEGER,
    assigned_team_id INTEGER,
    assigned_person_id INTEGER,
    vendor_id INTEGER,
    checklist_template_id INTEGER,
    compliance_standard TEXT,
    regulatory_reference TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','paused','completed','archived')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_person_id INTEGER,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (assigned_team_id) REFERENCES teams(id),
    FOREIGN KEY (assigned_person_id) REFERENCES people(id),
    FOREIGN KEY (vendor_id) REFERENCES companies(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id),
    FOREIGN KEY (created_by_person_id) REFERENCES people(id)
);

-- maintenance_plan_tasks — junction: which tasks belong to which plan
CREATE TABLE maintenance_plan_tasks (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    maintenance_plan_id INTEGER NOT NULL,
    maintenance_task_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (maintenance_plan_id) REFERENCES maintenance_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (maintenance_task_id) REFERENCES maintenance_tasks(id),
    UNIQUE(maintenance_plan_id, maintenance_task_id)
);

-- inspections — recurring inspection schedules
CREATE TABLE inspections (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    description TEXT,
    inspection_type TEXT NOT NULL DEFAULT 'routine'
        CHECK (inspection_type IN ('safety','compliance','routine','condition','regulatory','quality')),
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    recurrence TEXT NOT NULL DEFAULT 'monthly'
        CHECK (recurrence IN ('daily','weekly','biweekly','monthly','quarterly',
                              'semi_annual','annual','custom')),
    custom_interval_days INTEGER,
    start_date DATE NOT NULL,
    end_date DATE,
    next_due_date DATE NOT NULL,
    last_generated_at TIMESTAMPTZ,
    lead_time_days INTEGER NOT NULL DEFAULT 1,
    site_id INTEGER,
    room_id INTEGER,
    asset_id INTEGER,
    assigned_person_id INTEGER,
    assigned_team_id INTEGER,
    checklist_template_id INTEGER,
    compliance_standard TEXT,
    regulatory_reference TEXT,
    certification_required BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','paused','completed','archived')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_person_id INTEGER,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (assigned_person_id) REFERENCES people(id),
    FOREIGN KEY (assigned_team_id) REFERENCES teams(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id),
    FOREIGN KEY (created_by_person_id) REFERENCES people(id)
);

-- work_orders — actual instances of maintenance work
CREATE TABLE work_orders (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    wo_number TEXT,
    title TEXT NOT NULL,
    description TEXT,
    wo_type TEXT NOT NULL DEFAULT 'preventive'
        CHECK (wo_type IN ('preventive','corrective','emergency','inspection','condition_based')),
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','scheduled','in_progress','on_hold','completed',
                          'cancelled','overdue')),
    maintenance_plan_id INTEGER,
    source TEXT NOT NULL DEFAULT 'manual'
        CHECK (source IN ('manual','scheduled','ticket','inspection_failure')),
    source_ticket_id INTEGER,
    site_id INTEGER,
    room_id INTEGER,
    asset_id INTEGER,
    assigned_team_id INTEGER,
    assigned_person_id INTEGER,
    vendor_id INTEGER,
    vendor_reference TEXT,
    due_date DATE,
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    estimated_cost NUMERIC(10,2),
    actual_cost NUMERIC(10,2),
    cost_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    estimated_duration_minutes INTEGER,
    actual_duration_minutes INTEGER,
    checklist_template_id INTEGER,
    checklist_template_version INTEGER,
    findings TEXT,
    resolution TEXT,
    follow_up_needed BOOLEAN NOT NULL DEFAULT FALSE,
    follow_up_notes TEXT,
    completed_by_person_id INTEGER,
    approved_by_person_id INTEGER,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (maintenance_plan_id) REFERENCES maintenance_plans(id),
    FOREIGN KEY (source_ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (assigned_team_id) REFERENCES teams(id),
    FOREIGN KEY (assigned_person_id) REFERENCES people(id),
    FOREIGN KEY (vendor_id) REFERENCES companies(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id),
    FOREIGN KEY (completed_by_person_id) REFERENCES people(id),
    FOREIGN KEY (approved_by_person_id) REFERENCES people(id)
);

-- inspection_records — actual performed inspection instances
CREATE TABLE inspection_records (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    inspection_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled','in_progress','completed','failed','cancelled')),
    source TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (source IN ('scheduled','manual','follow_up')),
    inspector_person_id INTEGER,
    reviewer_person_id INTEGER,
    site_id INTEGER,
    room_id INTEGER,
    asset_id INTEGER,
    scheduled_date DATE,
    performed_date DATE,
    due_date DATE,
    overall_result TEXT
        CHECK (overall_result IN ('pass','fail','partial','na')),
    findings TEXT,
    corrective_actions TEXT,
    follow_up_needed BOOLEAN NOT NULL DEFAULT FALSE,
    follow_up_notes TEXT,
    checklist_template_id INTEGER,
    checklist_template_version INTEGER,
    certification_number TEXT,
    compliance_standard TEXT,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (inspection_id) REFERENCES inspections(id),
    FOREIGN KEY (inspector_person_id) REFERENCES people(id),
    FOREIGN KEY (reviewer_person_id) REFERENCES people(id),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (checklist_template_id) REFERENCES checklist_templates(id)
);

-- checklist_responses — actual checklist answers (shared by work orders and inspection records)
CREATE TABLE checklist_responses (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    work_order_id INTEGER,
    inspection_record_id INTEGER,
    checklist_template_item_id INTEGER NOT NULL,
    response_pass_fail TEXT CHECK (response_pass_fail IN ('pass','fail','na')),
    response_yes_no TEXT CHECK (response_yes_no IN ('yes','no','na')),
    response_numeric NUMERIC(10,2),
    response_text TEXT,
    response_photo_path TEXT,
    response_rating INTEGER CHECK (response_rating BETWEEN 1 AND 5),
    is_within_spec BOOLEAN,
    is_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    responded_by_person_id INTEGER,
    responded_at TIMESTAMPTZ DEFAULT NOW(),
    generated_ticket_id INTEGER,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (inspection_record_id) REFERENCES inspection_records(id) ON DELETE CASCADE,
    FOREIGN KEY (checklist_template_item_id) REFERENCES checklist_template_items(id),
    FOREIGN KEY (responded_by_person_id) REFERENCES people(id),
    FOREIGN KEY (generated_ticket_id) REFERENCES tickets(id),
    CHECK (
        (work_order_id IS NOT NULL AND inspection_record_id IS NULL) OR
        (work_order_id IS NULL AND inspection_record_id IS NOT NULL)
    )
);

-- work_order_parts — inventory items consumed during maintenance
CREATE TABLE work_order_parts (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    work_order_id INTEGER NOT NULL,
    inventory_item_id INTEGER NOT NULL,
    quantity_used INTEGER NOT NULL DEFAULT 1,
    unit_cost NUMERIC(10,2),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id)
);

-- ============================================================
-- 3. TRIGGER FUNCTION + TRIGGERS
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER assets_updated_at
    BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER technical_issues_updated_at
    BEFORE UPDATE ON technical_issues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER inventory_stock_updated_at
    BEFORE UPDATE ON inventory_stock
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER knowledge_articles_updated_at
    BEFORE UPDATE ON knowledge_articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER misc_knowledge_updated_at
    BEFORE UPDATE ON misc_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER project_tasks_updated_at
    BEFORE UPDATE ON project_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER auth_users_updated_at
    BEFORE UPDATE ON auth_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER instances_updated_at
    BEFORE UPDATE ON instances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER reminders_updated_at
    BEFORE UPDATE ON reminders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER bookings_updated_at
    BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER maintenance_tasks_updated_at
    BEFORE UPDATE ON maintenance_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER checklist_templates_updated_at
    BEFORE UPDATE ON checklist_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER maintenance_plans_updated_at
    BEFORE UPDATE ON maintenance_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER inspections_updated_at
    BEFORE UPDATE ON inspections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER work_orders_updated_at
    BEFORE UPDATE ON work_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER inspection_records_updated_at
    BEFORE UPDATE ON inspection_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER licenses_updated_at
    BEFORE UPDATE ON licenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-record asset lifecycle status changes
CREATE OR REPLACE FUNCTION track_asset_status_change()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.lifecycle_status IS DISTINCT FROM NEW.lifecycle_status THEN
        INSERT INTO asset_status_history (instance_id, asset_id, old_status, new_status)
        VALUES (NEW.instance_id, NEW.id, OLD.lifecycle_status, NEW.lifecycle_status);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_asset_status_history
    AFTER UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION track_asset_status_change();

-- Working-days helper for ticket due_date
CREATE OR REPLACE FUNCTION add_working_days(start_date DATE, n INTEGER)
RETURNS DATE LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
  result DATE := start_date;
  added  INTEGER := 0;
BEGIN
  WHILE added < n LOOP
    result := result + 1;
    IF EXTRACT(DOW FROM result) NOT IN (0, 6) THEN
      added := added + 1;
    END IF;
  END LOOP;
  RETURN result;
END;
$$;

CREATE OR REPLACE FUNCTION set_ticket_due_date()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.due_date IS NULL THEN
    NEW.due_date := add_working_days(NEW.opened_at::date, 3);
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_ticket_due_date
  BEFORE INSERT ON tickets
  FOR EACH ROW EXECUTE FUNCTION set_ticket_due_date();

-- Auto-generate work order number on insert
CREATE OR REPLACE FUNCTION set_wo_number()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  next_seq INTEGER;
BEGIN
  IF NEW.wo_number IS NULL THEN
    SELECT COALESCE(MAX(
      CAST(SUBSTRING(wo_number FROM 'WO-\d{4}-(\d+)') AS INTEGER)
    ), 0) + 1 INTO next_seq
    FROM work_orders
    WHERE instance_id = NEW.instance_id;
    NEW.wo_number := 'WO-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD(next_seq::TEXT, 4, '0');
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_work_order_number
    BEFORE INSERT ON work_orders
    FOR EACH ROW EXECUTE FUNCTION set_wo_number();

-- Auto-set work order due date (5 working days if not specified)
CREATE OR REPLACE FUNCTION set_wo_due_date()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.due_date IS NULL THEN
    NEW.due_date := add_working_days(CURRENT_DATE, 5);
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_wo_due_date
    BEFORE INSERT ON work_orders
    FOR EACH ROW EXECUTE FUNCTION set_wo_due_date();

-- ============================================================
-- 4. COMPOSITE UNIQUE INDEXES (per-instance uniqueness)
-- ============================================================

CREATE UNIQUE INDEX uq_assets_asset_tag_instance ON assets(instance_id, asset_tag);
CREATE UNIQUE INDEX uq_people_username_instance ON people(instance_id, username);
CREATE UNIQUE INDEX uq_tickets_ticket_number_instance ON tickets(instance_id, ticket_number);
CREATE UNIQUE INDEX uq_inventory_items_sku_instance ON inventory_items(instance_id, sku);
CREATE UNIQUE INDEX uq_tags_name_instance ON tags(instance_id, name);
CREATE UNIQUE INDEX uq_wo_number_instance ON work_orders(instance_id, wo_number);

-- Floor/Zone hierarchy indexes
CREATE INDEX idx_floors_site ON floors(site_id);
CREATE INDEX idx_zones_floor ON zones(floor_id);
CREATE UNIQUE INDEX uq_floors_code_site ON floors(instance_id, site_id, code) WHERE code IS NOT NULL;
CREATE UNIQUE INDEX uq_zones_code_floor ON zones(instance_id, floor_id, code) WHERE code IS NOT NULL;
CREATE INDEX idx_rooms_floor ON rooms(floor_id) WHERE floor_id IS NOT NULL;
CREATE INDEX idx_rooms_zone ON rooms(zone_id) WHERE zone_id IS NOT NULL;
CREATE INDEX idx_desks_floor ON desks(floor_id) WHERE floor_id IS NOT NULL;
CREATE INDEX idx_desks_zone ON desks(zone_id) WHERE zone_id IS NOT NULL;
CREATE INDEX idx_parking_spaces_floor ON parking_spaces(floor_id) WHERE floor_id IS NOT NULL;
CREATE INDEX idx_parking_spaces_zone ON parking_spaces(zone_id) WHERE zone_id IS NOT NULL;
CREATE INDEX idx_lockers_floor ON lockers(floor_id) WHERE floor_id IS NOT NULL;
CREATE INDEX idx_lockers_zone ON lockers(zone_id) WHERE zone_id IS NOT NULL;

-- Procurement / Purchase Requests
CREATE TABLE procurement_requests (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    requested_by_person_id INTEGER NOT NULL REFERENCES people(id),
    value NUMERIC(12, 2),
    item_description TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    vendor TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    reviewed_by_person_id INTEGER REFERENCES people(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_procurement_requests_status ON procurement_requests(instance_id, status);

CREATE TABLE procurement_updates (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    procurement_request_id INTEGER NOT NULL REFERENCES procurement_requests(id),
    author_person_id INTEGER REFERENCES people(id),
    event_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_procurement_updates_request ON procurement_updates(procurement_request_id, created_at);

-- ============================================================
-- SERVICE CATALOG & REQUEST FULFILLMENT
-- ============================================================

-- Available services that can be requested
CREATE TABLE service_catalog (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'general'
        CHECK (category IN ('onboarding','offboarding','workplace','it_access',
                            'equipment','facilities','av_support','security',
                            'moves','general')),
    estimated_fulfillment_days INTEGER,
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    approval_person_id INTEGER REFERENCES people(id),
    owner_person_id INTEGER REFERENCES people(id),
    owner_team_id INTEGER REFERENCES teams(id),
    site_id INTEGER REFERENCES sites(id),
    keywords TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','inactive','archived')),
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_by_person_id INTEGER REFERENCES people(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uq_service_catalog_name_instance ON service_catalog(instance_id, name);

-- Form fields that define what info is collected when requesting a service
CREATE TABLE service_request_templates (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    service_catalog_id INTEGER NOT NULL REFERENCES service_catalog(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    field_label TEXT NOT NULL,
    field_type TEXT NOT NULL DEFAULT 'text'
        CHECK (field_type IN ('text','textarea','date','datetime','number',
                              'select','person','site','room','desk','asset','boolean')),
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    select_options TEXT,
    help_text TEXT,
    default_value TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_service_request_templates_catalog ON service_request_templates(service_catalog_id);

-- Template steps/workflow to complete a service
CREATE TABLE request_fulfillment_tasks (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    service_catalog_id INTEGER NOT NULL REFERENCES service_catalog(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    assigned_person_id INTEGER REFERENCES people(id),
    assigned_team_id INTEGER REFERENCES teams(id),
    estimated_duration_minutes INTEGER,
    depends_on_task_id INTEGER REFERENCES request_fulfillment_tasks(id),
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    auto_create_ticket BOOLEAN NOT NULL DEFAULT FALSE,
    auto_create_work_order BOOLEAN NOT NULL DEFAULT FALSE,
    checklist_template_id INTEGER REFERENCES checklist_templates(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_request_fulfillment_tasks_catalog ON request_fulfillment_tasks(service_catalog_id);

-- Actual submitted service requests
CREATE TABLE service_requests (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    sr_number TEXT,
    service_catalog_id INTEGER NOT NULL REFERENCES service_catalog(id),
    ticket_id INTEGER REFERENCES tickets(id),
    requester_person_id INTEGER NOT NULL REFERENCES people(id),
    on_behalf_of_person_id INTEGER REFERENCES people(id),
    site_id INTEGER REFERENCES sites(id),
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    status TEXT NOT NULL DEFAULT 'submitted'
        CHECK (status IN ('submitted','pending_approval','approved','in_progress',
                          'on_hold','completed','cancelled','rejected')),
    form_data JSONB,
    approved_by_person_id INTEGER REFERENCES people(id),
    approved_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    due_date DATE,
    notes TEXT,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uq_sr_number_instance ON service_requests(instance_id, sr_number);
CREATE INDEX idx_service_requests_status ON service_requests(instance_id, status);

-- Per-request task completion tracking
CREATE TABLE service_request_task_progress (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    service_request_id INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    fulfillment_task_id INTEGER NOT NULL REFERENCES request_fulfillment_tasks(id),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','in_progress','completed','skipped','blocked')),
    assigned_person_id INTEGER REFERENCES people(id),
    linked_ticket_id INTEGER REFERENCES tickets(id),
    linked_work_order_id INTEGER REFERENCES work_orders(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    completed_by_person_id INTEGER REFERENCES people(id),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(service_request_id, fulfillment_task_id)
);
CREATE INDEX idx_service_request_task_progress_request ON service_request_task_progress(service_request_id);

-- Service catalog triggers (must come after table definitions above)
CREATE TRIGGER service_catalog_updated_at
    BEFORE UPDATE ON service_catalog
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER request_fulfillment_tasks_updated_at
    BEFORE UPDATE ON request_fulfillment_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER service_requests_updated_at
    BEFORE UPDATE ON service_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER service_request_task_progress_updated_at
    BEFORE UPDATE ON service_request_task_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-generate service request number on insert
CREATE OR REPLACE FUNCTION set_sr_number()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  next_seq INTEGER;
BEGIN
  IF NEW.sr_number IS NULL THEN
    SELECT COALESCE(MAX(
      CAST(SUBSTRING(sr_number FROM 'SR-\d{4}-(\d+)') AS INTEGER)
    ), 0) + 1 INTO next_seq
    FROM service_requests
    WHERE instance_id = NEW.instance_id;
    NEW.sr_number := 'SR-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD(next_seq::TEXT, 4, '0');
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_service_request_number
    BEFORE INSERT ON service_requests
    FOR EACH ROW EXECUTE FUNCTION set_sr_number();

-- ============================================================
-- 5. ROW-LEVEL SECURITY POLICIES (all tenant-scoped tables)
-- ============================================================

-- companies
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies FORCE ROW LEVEL SECURITY;
CREATE POLICY companies_tenant_isolation ON companies
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY companies_tenant_insert ON companies
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- sites
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE sites FORCE ROW LEVEL SECURITY;
CREATE POLICY sites_tenant_isolation ON sites
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY sites_tenant_insert ON sites
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- floors
ALTER TABLE floors ENABLE ROW LEVEL SECURITY;
ALTER TABLE floors FORCE ROW LEVEL SECURITY;
CREATE POLICY floors_tenant_isolation ON floors
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY floors_tenant_insert ON floors
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- zones
ALTER TABLE zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE zones FORCE ROW LEVEL SECURITY;
CREATE POLICY zones_tenant_isolation ON zones
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY zones_tenant_insert ON zones
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- rooms
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms FORCE ROW LEVEL SECURITY;
CREATE POLICY rooms_tenant_isolation ON rooms
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY rooms_tenant_insert ON rooms
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- teams
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams FORCE ROW LEVEL SECURITY;
CREATE POLICY teams_tenant_isolation ON teams
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY teams_tenant_insert ON teams
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- people
ALTER TABLE people ENABLE ROW LEVEL SECURITY;
ALTER TABLE people FORCE ROW LEVEL SECURITY;
CREATE POLICY people_tenant_isolation ON people
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY people_tenant_insert ON people
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- pto
ALTER TABLE pto ENABLE ROW LEVEL SECURITY;
ALTER TABLE pto FORCE ROW LEVEL SECURITY;
CREATE POLICY pto_tenant_isolation ON pto
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY pto_tenant_insert ON pto
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- assets
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets FORCE ROW LEVEL SECURITY;
CREATE POLICY assets_tenant_isolation ON assets
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY assets_tenant_insert ON assets
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- asset_relationships
ALTER TABLE asset_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_relationships FORCE ROW LEVEL SECURITY;
CREATE POLICY asset_relationships_tenant_isolation ON asset_relationships
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY asset_relationships_tenant_insert ON asset_relationships
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- asset_status_history
ALTER TABLE asset_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_status_history FORCE ROW LEVEL SECURITY;
CREATE POLICY asset_status_history_tenant_isolation ON asset_status_history
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY asset_status_history_tenant_insert ON asset_status_history
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- asset_assignments
ALTER TABLE asset_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_assignments FORCE ROW LEVEL SECURITY;
CREATE POLICY asset_assignments_tenant_isolation ON asset_assignments
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY asset_assignments_tenant_insert ON asset_assignments
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- licenses
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE licenses FORCE ROW LEVEL SECURITY;
CREATE POLICY licenses_tenant_isolation ON licenses
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY licenses_tenant_insert ON licenses
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- software_installations
ALTER TABLE software_installations ENABLE ROW LEVEL SECURITY;
ALTER TABLE software_installations FORCE ROW LEVEL SECURITY;
CREATE POLICY software_installations_tenant_isolation ON software_installations
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY software_installations_tenant_insert ON software_installations
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- asset_documents
ALTER TABLE asset_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_documents FORCE ROW LEVEL SECURITY;
CREATE POLICY asset_documents_tenant_isolation ON asset_documents
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY asset_documents_tenant_insert ON asset_documents
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- disposal_records
ALTER TABLE disposal_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE disposal_records FORCE ROW LEVEL SECURITY;
CREATE POLICY disposal_records_tenant_isolation ON disposal_records
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY disposal_records_tenant_insert ON disposal_records
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- tickets
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets FORCE ROW LEVEL SECURITY;
CREATE POLICY tickets_tenant_isolation ON tickets
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY tickets_tenant_insert ON tickets
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- ticket_replies
ALTER TABLE ticket_replies ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_replies FORCE ROW LEVEL SECURITY;
CREATE POLICY ticket_replies_tenant_isolation ON ticket_replies
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY ticket_replies_tenant_insert ON ticket_replies
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- ticket_watchers
ALTER TABLE ticket_watchers ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_watchers FORCE ROW LEVEL SECURITY;
CREATE POLICY ticket_watchers_tenant_isolation ON ticket_watchers
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY ticket_watchers_tenant_insert ON ticket_watchers
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- ticket_attachments
ALTER TABLE ticket_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_attachments FORCE ROW LEVEL SECURITY;
CREATE POLICY ticket_attachments_tenant_isolation ON ticket_attachments
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY ticket_attachments_tenant_insert ON ticket_attachments
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- ticket_timeline
ALTER TABLE ticket_timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_timeline FORCE ROW LEVEL SECURITY;
CREATE POLICY ticket_timeline_tenant_isolation ON ticket_timeline
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY ticket_timeline_tenant_insert ON ticket_timeline
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- technical_issues
ALTER TABLE technical_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE technical_issues FORCE ROW LEVEL SECURITY;
CREATE POLICY technical_issues_tenant_isolation ON technical_issues
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY technical_issues_tenant_insert ON technical_issues
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- issue_occurrences
ALTER TABLE issue_occurrences ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_occurrences FORCE ROW LEVEL SECURITY;
CREATE POLICY issue_occurrences_tenant_isolation ON issue_occurrences
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY issue_occurrences_tenant_insert ON issue_occurrences
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- events
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE events FORCE ROW LEVEL SECURITY;
CREATE POLICY events_tenant_isolation ON events
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY events_tenant_insert ON events
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- event_participants
ALTER TABLE event_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_participants FORCE ROW LEVEL SECURITY;
CREATE POLICY event_participants_tenant_isolation ON event_participants
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY event_participants_tenant_insert ON event_participants
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- event_assets
ALTER TABLE event_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_assets FORCE ROW LEVEL SECURITY;
CREATE POLICY event_assets_tenant_isolation ON event_assets
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY event_assets_tenant_insert ON event_assets
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- notes
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes FORCE ROW LEVEL SECURITY;
CREATE POLICY notes_tenant_isolation ON notes
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY notes_tenant_insert ON notes
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- work_logs
ALTER TABLE work_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_logs FORCE ROW LEVEL SECURITY;
CREATE POLICY work_logs_tenant_isolation ON work_logs
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY work_logs_tenant_insert ON work_logs
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- inventory_items
ALTER TABLE inventory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_items FORCE ROW LEVEL SECURITY;
CREATE POLICY inventory_items_tenant_isolation ON inventory_items
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY inventory_items_tenant_insert ON inventory_items
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- inventory_stock
ALTER TABLE inventory_stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_stock FORCE ROW LEVEL SECURITY;
CREATE POLICY inventory_stock_tenant_isolation ON inventory_stock
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY inventory_stock_tenant_insert ON inventory_stock
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- inventory_transactions
ALTER TABLE inventory_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_transactions FORCE ROW LEVEL SECURITY;
CREATE POLICY inventory_transactions_tenant_isolation ON inventory_transactions
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY inventory_transactions_tenant_insert ON inventory_transactions
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- changes
ALTER TABLE changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE changes FORCE ROW LEVEL SECURITY;
CREATE POLICY changes_tenant_isolation ON changes
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY changes_tenant_insert ON changes
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- vendor_contracts
ALTER TABLE vendor_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_contracts FORCE ROW LEVEL SECURITY;
CREATE POLICY vendor_contracts_tenant_isolation ON vendor_contracts
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY vendor_contracts_tenant_insert ON vendor_contracts
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- projects
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
CREATE POLICY projects_tenant_isolation ON projects
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY projects_tenant_insert ON projects
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- project_members
ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_members FORCE ROW LEVEL SECURITY;
CREATE POLICY project_members_tenant_isolation ON project_members
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY project_members_tenant_insert ON project_members
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- project_tasks
ALTER TABLE project_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_tasks FORCE ROW LEVEL SECURITY;
CREATE POLICY project_tasks_tenant_isolation ON project_tasks
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY project_tasks_tenant_insert ON project_tasks
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- project_updates
ALTER TABLE project_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_updates FORCE ROW LEVEL SECURITY;
CREATE POLICY project_updates_tenant_isolation ON project_updates
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY project_updates_tenant_insert ON project_updates
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- project_expenses
ALTER TABLE project_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_expenses FORCE ROW LEVEL SECURITY;
CREATE POLICY project_expenses_tenant_isolation ON project_expenses
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY project_expenses_tenant_insert ON project_expenses
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- project_links
ALTER TABLE project_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_links FORCE ROW LEVEL SECURITY;
CREATE POLICY project_links_tenant_isolation ON project_links
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY project_links_tenant_insert ON project_links
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- misc_knowledge
ALTER TABLE misc_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE misc_knowledge FORCE ROW LEVEL SECURITY;
CREATE POLICY misc_knowledge_tenant_isolation ON misc_knowledge
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY misc_knowledge_tenant_insert ON misc_knowledge
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- knowledge_articles
ALTER TABLE knowledge_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_articles FORCE ROW LEVEL SECURITY;
CREATE POLICY knowledge_articles_tenant_isolation ON knowledge_articles
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY knowledge_articles_tenant_insert ON knowledge_articles
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- workflows
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows FORCE ROW LEVEL SECURITY;
CREATE POLICY workflows_tenant_isolation ON workflows
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY workflows_tenant_insert ON workflows
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- tags
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags FORCE ROW LEVEL SECURITY;
CREATE POLICY tags_tenant_isolation ON tags
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY tags_tenant_insert ON tags
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- entity_tags
ALTER TABLE entity_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_tags FORCE ROW LEVEL SECURITY;
CREATE POLICY entity_tags_tenant_isolation ON entity_tags
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY entity_tags_tenant_insert ON entity_tags
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- audit_log
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_log_tenant_isolation ON audit_log
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY audit_log_tenant_insert ON audit_log
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- app_settings
ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_settings FORCE ROW LEVEL SECURITY;
CREATE POLICY app_settings_tenant_isolation ON app_settings
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY app_settings_tenant_insert ON app_settings
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- chat_sessions
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions FORCE ROW LEVEL SECURITY;
CREATE POLICY chat_sessions_tenant_isolation ON chat_sessions
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY chat_sessions_tenant_insert ON chat_sessions
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- chat_messages
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages FORCE ROW LEVEL SECURITY;
CREATE POLICY chat_messages_tenant_isolation ON chat_messages
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY chat_messages_tenant_insert ON chat_messages
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- approval_rules
ALTER TABLE approval_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_rules FORCE ROW LEVEL SECURITY;
CREATE POLICY approval_rules_tenant_isolation ON approval_rules
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY approval_rules_tenant_insert ON approval_rules
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- pending_approvals
ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_approvals FORCE ROW LEVEL SECURITY;
CREATE POLICY pending_approvals_tenant_isolation ON pending_approvals
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY pending_approvals_tenant_insert ON pending_approvals
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- inbound_email_senders
ALTER TABLE inbound_email_senders ENABLE ROW LEVEL SECURITY;
ALTER TABLE inbound_email_senders FORCE ROW LEVEL SECURITY;
CREATE POLICY inbound_email_senders_tenant_isolation ON inbound_email_senders
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY inbound_email_senders_tenant_insert ON inbound_email_senders
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- reminders
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders FORCE ROW LEVEL SECURITY;
CREATE POLICY reminders_tenant_isolation ON reminders
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY reminders_tenant_insert ON reminders
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- inbound_emails
ALTER TABLE inbound_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE inbound_emails FORCE ROW LEVEL SECURITY;
CREATE POLICY inbound_emails_tenant_isolation ON inbound_emails
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY inbound_emails_tenant_insert ON inbound_emails
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- desks
ALTER TABLE desks ENABLE ROW LEVEL SECURITY;
ALTER TABLE desks FORCE ROW LEVEL SECURITY;
CREATE POLICY desks_tenant_isolation ON desks
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY desks_tenant_insert ON desks
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- parking_spaces
ALTER TABLE parking_spaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE parking_spaces FORCE ROW LEVEL SECURITY;
CREATE POLICY parking_spaces_tenant_isolation ON parking_spaces
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY parking_spaces_tenant_insert ON parking_spaces
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- lockers
ALTER TABLE lockers ENABLE ROW LEVEL SECURITY;
ALTER TABLE lockers FORCE ROW LEVEL SECURITY;
CREATE POLICY lockers_tenant_isolation ON lockers
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY lockers_tenant_insert ON lockers
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- bookings
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings FORCE ROW LEVEL SECURITY;
CREATE POLICY bookings_tenant_isolation ON bookings
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY bookings_tenant_insert ON bookings
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- maintenance_tasks
ALTER TABLE maintenance_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_tasks FORCE ROW LEVEL SECURITY;
CREATE POLICY maintenance_tasks_tenant_isolation ON maintenance_tasks
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY maintenance_tasks_tenant_insert ON maintenance_tasks
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- checklist_templates
ALTER TABLE checklist_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_templates FORCE ROW LEVEL SECURITY;
CREATE POLICY checklist_templates_tenant_isolation ON checklist_templates
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY checklist_templates_tenant_insert ON checklist_templates
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- checklist_template_items
ALTER TABLE checklist_template_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_template_items FORCE ROW LEVEL SECURITY;
CREATE POLICY checklist_template_items_tenant_isolation ON checklist_template_items
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY checklist_template_items_tenant_insert ON checklist_template_items
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- maintenance_plans
ALTER TABLE maintenance_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_plans FORCE ROW LEVEL SECURITY;
CREATE POLICY maintenance_plans_tenant_isolation ON maintenance_plans
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY maintenance_plans_tenant_insert ON maintenance_plans
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- maintenance_plan_tasks
ALTER TABLE maintenance_plan_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_plan_tasks FORCE ROW LEVEL SECURITY;
CREATE POLICY maintenance_plan_tasks_tenant_isolation ON maintenance_plan_tasks
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY maintenance_plan_tasks_tenant_insert ON maintenance_plan_tasks
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- inspections
ALTER TABLE inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspections FORCE ROW LEVEL SECURITY;
CREATE POLICY inspections_tenant_isolation ON inspections
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY inspections_tenant_insert ON inspections
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- work_orders
ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_orders FORCE ROW LEVEL SECURITY;
CREATE POLICY work_orders_tenant_isolation ON work_orders
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY work_orders_tenant_insert ON work_orders
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- inspection_records
ALTER TABLE inspection_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_records FORCE ROW LEVEL SECURITY;
CREATE POLICY inspection_records_tenant_isolation ON inspection_records
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY inspection_records_tenant_insert ON inspection_records
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- checklist_responses
ALTER TABLE checklist_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_responses FORCE ROW LEVEL SECURITY;
CREATE POLICY checklist_responses_tenant_isolation ON checklist_responses
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY checklist_responses_tenant_insert ON checklist_responses
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- work_order_parts
ALTER TABLE work_order_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_order_parts FORCE ROW LEVEL SECURITY;
CREATE POLICY work_order_parts_tenant_isolation ON work_order_parts
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY work_order_parts_tenant_insert ON work_order_parts
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- procurement_requests
ALTER TABLE procurement_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE procurement_requests FORCE ROW LEVEL SECURITY;
CREATE POLICY procurement_requests_tenant_isolation ON procurement_requests
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY procurement_requests_tenant_insert ON procurement_requests
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- procurement_updates
ALTER TABLE procurement_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE procurement_updates FORCE ROW LEVEL SECURITY;
CREATE POLICY procurement_updates_tenant_isolation ON procurement_updates
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY procurement_updates_tenant_insert ON procurement_updates
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- service_catalog
ALTER TABLE service_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_catalog FORCE ROW LEVEL SECURITY;
CREATE POLICY service_catalog_tenant_isolation ON service_catalog
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY service_catalog_tenant_insert ON service_catalog
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- service_request_templates
ALTER TABLE service_request_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_request_templates FORCE ROW LEVEL SECURITY;
CREATE POLICY service_request_templates_tenant_isolation ON service_request_templates
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY service_request_templates_tenant_insert ON service_request_templates
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- request_fulfillment_tasks
ALTER TABLE request_fulfillment_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE request_fulfillment_tasks FORCE ROW LEVEL SECURITY;
CREATE POLICY request_fulfillment_tasks_tenant_isolation ON request_fulfillment_tasks
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY request_fulfillment_tasks_tenant_insert ON request_fulfillment_tasks
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- service_requests
ALTER TABLE service_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_requests FORCE ROW LEVEL SECURITY;
CREATE POLICY service_requests_tenant_isolation ON service_requests
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY service_requests_tenant_insert ON service_requests
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- service_request_task_progress
ALTER TABLE service_request_task_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_request_task_progress FORCE ROW LEVEL SECURITY;
CREATE POLICY service_request_task_progress_tenant_isolation ON service_request_task_progress
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY service_request_task_progress_tenant_insert ON service_request_task_progress
    FOR INSERT WITH CHECK (instance_id = current_setting('app.current_instance_id', true)::bigint);

-- ============================================================
-- 6. INSTANCE_ID B-TREE INDEXES (all tenant-scoped tables)
-- ============================================================

CREATE INDEX idx_companies_instance ON companies(instance_id);
CREATE INDEX idx_sites_instance ON sites(instance_id);
CREATE INDEX idx_rooms_instance ON rooms(instance_id);
CREATE INDEX idx_teams_instance ON teams(instance_id);
CREATE INDEX idx_people_instance ON people(instance_id);
CREATE INDEX idx_pto_instance ON pto(instance_id);
CREATE INDEX idx_assets_instance ON assets(instance_id);
CREATE INDEX idx_asset_relationships_instance ON asset_relationships(instance_id);
CREATE INDEX idx_asset_status_history_instance ON asset_status_history(instance_id);
CREATE INDEX idx_asset_assignments_instance ON asset_assignments(instance_id);
CREATE INDEX idx_licenses_instance ON licenses(instance_id);
CREATE INDEX idx_software_installations_instance ON software_installations(instance_id);
CREATE INDEX idx_asset_documents_instance ON asset_documents(instance_id);
CREATE INDEX idx_disposal_records_instance ON disposal_records(instance_id);
CREATE INDEX idx_tickets_instance ON tickets(instance_id);
CREATE INDEX idx_ticket_replies_instance ON ticket_replies(instance_id);
CREATE INDEX idx_ticket_watchers_instance ON ticket_watchers(instance_id);
CREATE INDEX idx_ticket_attachments_instance ON ticket_attachments(instance_id);
CREATE INDEX idx_ticket_timeline_instance ON ticket_timeline(instance_id);
CREATE INDEX idx_technical_issues_instance ON technical_issues(instance_id);
CREATE INDEX idx_issue_occurrences_instance ON issue_occurrences(instance_id);
CREATE INDEX idx_events_instance ON events(instance_id);
CREATE INDEX idx_event_participants_instance ON event_participants(instance_id);
CREATE INDEX idx_event_assets_instance ON event_assets(instance_id);
CREATE INDEX idx_notes_instance ON notes(instance_id);
CREATE INDEX idx_work_logs_instance ON work_logs(instance_id);
CREATE INDEX idx_inventory_items_instance ON inventory_items(instance_id);
CREATE INDEX idx_inventory_stock_instance ON inventory_stock(instance_id);
CREATE INDEX idx_inventory_transactions_instance ON inventory_transactions(instance_id);
CREATE INDEX idx_changes_instance ON changes(instance_id);
CREATE INDEX idx_vendor_contracts_instance ON vendor_contracts(instance_id);
CREATE INDEX idx_misc_knowledge_instance ON misc_knowledge(instance_id);
CREATE INDEX idx_knowledge_articles_instance ON knowledge_articles(instance_id);
CREATE INDEX idx_workflows_instance ON workflows(instance_id);
CREATE INDEX idx_tags_instance ON tags(instance_id);
CREATE INDEX idx_entity_tags_instance ON entity_tags(instance_id);
CREATE INDEX idx_audit_log_instance ON audit_log(instance_id);
CREATE INDEX idx_chat_sessions_instance ON chat_sessions(instance_id);
CREATE INDEX idx_chat_messages_instance ON chat_messages(instance_id);
CREATE INDEX idx_approval_rules_instance ON approval_rules(instance_id);
CREATE INDEX idx_pending_approvals_instance ON pending_approvals(instance_id);
CREATE INDEX idx_projects_instance ON projects(instance_id);
CREATE INDEX idx_project_members_instance ON project_members(instance_id);
CREATE INDEX idx_project_tasks_instance ON project_tasks(instance_id);
CREATE INDEX idx_project_updates_instance ON project_updates(instance_id);
CREATE INDEX idx_project_expenses_instance ON project_expenses(instance_id);
CREATE INDEX idx_project_links_instance ON project_links(instance_id);
CREATE INDEX idx_reminders_instance ON reminders(instance_id);
CREATE INDEX idx_reminders_due ON reminders(status, remind_at) WHERE status = 'active';
CREATE INDEX idx_desks_instance ON desks(instance_id);
CREATE INDEX idx_parking_spaces_instance ON parking_spaces(instance_id);
CREATE INDEX idx_lockers_instance ON lockers(instance_id);
CREATE INDEX idx_bookings_instance ON bookings(instance_id);
CREATE INDEX idx_bookings_resource ON bookings(instance_id, resource_type, resource_id, start_time, end_time);
CREATE INDEX idx_bookings_person ON bookings(instance_id, booked_by_person_id);
CREATE INDEX idx_maintenance_tasks_instance ON maintenance_tasks(instance_id);
CREATE INDEX idx_checklist_templates_instance ON checklist_templates(instance_id);
CREATE INDEX idx_checklist_template_items_instance ON checklist_template_items(instance_id);
CREATE INDEX idx_maintenance_plans_instance ON maintenance_plans(instance_id);
CREATE INDEX idx_maintenance_plans_due ON maintenance_plans(status, next_due_date) WHERE status = 'active';
CREATE INDEX idx_maintenance_plan_tasks_instance ON maintenance_plan_tasks(instance_id);
CREATE INDEX idx_inspections_instance ON inspections(instance_id);
CREATE INDEX idx_inspections_due ON inspections(status, next_due_date) WHERE status = 'active';
CREATE INDEX idx_work_orders_instance ON work_orders(instance_id);
CREATE INDEX idx_work_orders_status ON work_orders(instance_id, status);
CREATE INDEX idx_work_orders_asset ON work_orders(instance_id, asset_id) WHERE asset_id IS NOT NULL;
CREATE INDEX idx_work_orders_plan ON work_orders(instance_id, maintenance_plan_id) WHERE maintenance_plan_id IS NOT NULL;
CREATE INDEX idx_inspection_records_instance ON inspection_records(instance_id);
CREATE INDEX idx_inspection_records_inspection ON inspection_records(instance_id, inspection_id) WHERE inspection_id IS NOT NULL;
CREATE INDEX idx_checklist_responses_instance ON checklist_responses(instance_id);
CREATE INDEX idx_checklist_responses_wo ON checklist_responses(work_order_id) WHERE work_order_id IS NOT NULL;
CREATE INDEX idx_checklist_responses_ir ON checklist_responses(inspection_record_id) WHERE inspection_record_id IS NOT NULL;
CREATE INDEX idx_work_order_parts_instance ON work_order_parts(instance_id);
CREATE INDEX idx_procurement_requests_instance ON procurement_requests(instance_id);
CREATE INDEX idx_procurement_updates_instance ON procurement_updates(instance_id);
CREATE INDEX idx_service_catalog_instance ON service_catalog(instance_id);
CREATE INDEX idx_service_catalog_category ON service_catalog(instance_id, category) WHERE status = 'active';
CREATE INDEX idx_service_request_templates_instance ON service_request_templates(instance_id);
CREATE INDEX idx_request_fulfillment_tasks_instance ON request_fulfillment_tasks(instance_id);
CREATE INDEX idx_service_requests_instance ON service_requests(instance_id);
CREATE INDEX idx_service_request_task_progress_instance ON service_request_task_progress(instance_id);

-- Token usage logging for query metering observability
CREATE TABLE query_token_log (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    total_input_tokens INTEGER NOT NULL,
    total_output_tokens INTEGER NOT NULL,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    api_calls INTEGER NOT NULL DEFAULT 1,
    queries_consumed INTEGER NOT NULL DEFAULT 1,
    llm_provider TEXT,
    llm_model TEXT,
    tool_calls_attempted INTEGER NOT NULL DEFAULT 0,
    tool_calls_failed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_query_token_log_instance ON query_token_log(instance_id, created_at);

CREATE TABLE api_key_audit_log (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    action TEXT NOT NULL,
    performed_by BIGINT REFERENCES auth_users(id),
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
