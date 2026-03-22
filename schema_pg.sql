-- TrueCore.cloud Multi-Tenant SaaS — PostgreSQL Schema
-- Multi-tenant PostgreSQL schema
-- All tenant-scoped tables include instance_id with RLS enforcement

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
    query_pool_reset_at TIMESTAMPTZ,
    email_signature TEXT,
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

CREATE TABLE rooms (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL REFERENCES instances(id),
    site_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    capacity INTEGER,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (site_id) REFERENCES sites(id)
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
    warranty_expiry DATE,
    lifecycle_status TEXT DEFAULT 'active',
    ownership_type TEXT,
    site_id INTEGER,
    room_id INTEGER,
    assigned_to_person_id INTEGER,
    notes TEXT,
    important BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
    FOREIGN KEY (requester_person_id) REFERENCES people(id),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

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
    person_id INTEGER NOT NULL,
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

-- ============================================================
-- 4. COMPOSITE UNIQUE INDEXES (per-instance uniqueness)
-- ============================================================

CREATE UNIQUE INDEX uq_assets_asset_tag_instance ON assets(instance_id, asset_tag);
CREATE UNIQUE INDEX uq_people_username_instance ON people(instance_id, username);
CREATE UNIQUE INDEX uq_tickets_ticket_number_instance ON tickets(instance_id, ticket_number);
CREATE UNIQUE INDEX uq_inventory_items_sku_instance ON inventory_items(instance_id, sku);
CREATE UNIQUE INDEX uq_tags_name_instance ON tags(instance_id, name);

-- ============================================================
-- 5. ROW-LEVEL SECURITY POLICIES (all 33 tenant-scoped tables)
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

-- tickets
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets FORCE ROW LEVEL SECURITY;
CREATE POLICY tickets_tenant_isolation ON tickets
    USING (instance_id = current_setting('app.current_instance_id', true)::bigint);
CREATE POLICY tickets_tenant_insert ON tickets
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

-- ============================================================
-- 6. INSTANCE_ID B-TREE INDEXES (all 33 tenant-scoped tables)
-- ============================================================

CREATE INDEX idx_companies_instance ON companies(instance_id);
CREATE INDEX idx_sites_instance ON sites(instance_id);
CREATE INDEX idx_rooms_instance ON rooms(instance_id);
CREATE INDEX idx_teams_instance ON teams(instance_id);
CREATE INDEX idx_people_instance ON people(instance_id);
CREATE INDEX idx_pto_instance ON pto(instance_id);
CREATE INDEX idx_assets_instance ON assets(instance_id);
CREATE INDEX idx_asset_relationships_instance ON asset_relationships(instance_id);
CREATE INDEX idx_tickets_instance ON tickets(instance_id);
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
