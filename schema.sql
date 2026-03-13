-- MileCore Site Operations Database Schema
-- Full site operations schema for technical support environments

-- Core Infrastructure
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    client_name TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    timezone TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY,
    site_id INTEGER NOT NULL,
    parent_location_id INTEGER,
    name TEXT NOT NULL,
    location_type TEXT NOT NULL,
    code TEXT,
    description TEXT,
    capacity INTEGER,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (parent_location_id) REFERENCES locations(id)
);

-- People & Teams
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    role_title TEXT,
    person_type TEXT NOT NULL,
    department TEXT,
    company TEXT,
    site_id INTEGER,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    team_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    team_role TEXT,
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);

-- Assets
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    asset_tag TEXT UNIQUE,
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
    location_id INTEGER,
    assigned_to_person_id INTEGER,
    notes TEXT,
    important INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (assigned_to_person_id) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS asset_relationships (
    id INTEGER PRIMARY KEY,
    parent_asset_id INTEGER NOT NULL,
    child_asset_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_asset_id) REFERENCES assets(id),
    FOREIGN KEY (child_asset_id) REFERENCES assets(id)
);

-- Support & Issues
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY,
    request_number TEXT UNIQUE,
    requester_person_id INTEGER,
    site_id INTEGER,
    location_id INTEGER,
    asset_id INTEGER,
    request_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    source TEXT,
    assigned_team_id INTEGER,
    assigned_person_id INTEGER,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP,
    important INTEGER DEFAULT 0,
    FOREIGN KEY (requester_person_id) REFERENCES people(id),
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE TABLE IF NOT EXISTS technical_issues (
    id INTEGER PRIMARY KEY,
    request_id INTEGER,
    asset_id INTEGER,
    site_id INTEGER,
    location_id INTEGER,
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
    known_issue BOOLEAN DEFAULT 0,
    knowledgeworthy BOOLEAN DEFAULT 1,
    reported_by_person_id INTEGER,
    resolved_by_person_id INTEGER,
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    important INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS issue_occurrences (
    id INTEGER PRIMARY KEY,
    technical_issue_id INTEGER NOT NULL,
    asset_id INTEGER,
    request_id INTEGER,
    site_id INTEGER,
    location_id INTEGER,
    observed_by_person_id INTEGER,
    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    outcome TEXT,
    FOREIGN KEY (technical_issue_id) REFERENCES technical_issues(id)
);

-- Events & Activities
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    site_id INTEGER,
    location_id INTEGER,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'planned',
    owner_person_id INTEGER,
    related_request_id INTEGER,
    impact_level TEXT,
    important INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_participants (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    participant_role TEXT,
    attendance_status TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS event_assets (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    usage_role TEXT,
    notes TEXT,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

-- Notes & Work
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    note_type TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    site_id INTEGER,
    location_id INTEGER,
    asset_id INTEGER,
    request_id INTEGER,
    technical_issue_id INTEGER,
    event_id INTEGER,
    created_by_person_id INTEGER,
    visibility TEXT DEFAULT 'internal',
    important INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS work_logs (
    id INTEGER PRIMARY KEY,
    request_id INTEGER,
    technical_issue_id INTEGER,
    event_id INTEGER,
    asset_id INTEGER,
    person_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    time_spent_minutes INTEGER,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    important INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory
CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY,
    sku TEXT,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    unit_of_measure TEXT DEFAULT 'each',
    reorder_threshold INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_stock (
    id INTEGER PRIMARY KEY,
    inventory_item_id INTEGER NOT NULL,
    site_id INTEGER NOT NULL,
    location_id INTEGER,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id),
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id INTEGER PRIMARY KEY,
    inventory_item_id INTEGER NOT NULL,
    site_id INTEGER,
    location_id INTEGER,
    transaction_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    related_person_id INTEGER,
    related_request_id INTEGER,
    performed_by_person_id INTEGER,
    notes TEXT,
    important INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id)
);

-- Changes & Vendors
CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY,
    site_id INTEGER,
    location_id INTEGER,
    asset_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    change_type TEXT NOT NULL,
    risk_level TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'planned',
    requested_by_person_id INTEGER,
    implemented_by_person_id INTEGER,
    planned_start TIMESTAMP,
    planned_end TIMESTAMP,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    rollback_plan TEXT,
    outcome TEXT,
    important INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    vendor_type TEXT,
    support_email TEXT,
    support_phone TEXT,
    website TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS vendor_contracts (
    id INTEGER PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    site_id INTEGER,
    contract_name TEXT NOT NULL,
    contract_type TEXT,
    start_date DATE,
    end_date DATE,
    sla_description TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);

-- Knowledge & Metadata
CREATE TABLE IF NOT EXISTS knowledge_articles (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    article_type TEXT NOT NULL,
    category TEXT,
    brand TEXT,
    model TEXT,
    asset_type TEXT,
    site_id INTEGER,
    location_id INTEGER,
    created_by_person_id INTEGER,
    approved_by_person_id INTEGER,
    status TEXT DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_tags (
    id INTEGER PRIMARY KEY,
    tag_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    changed_by_person_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Users & Chat Persistence
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);

-- Auto-update updated_at on row changes
CREATE TRIGGER IF NOT EXISTS assets_updated_at AFTER UPDATE ON assets
BEGIN UPDATE assets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS technical_issues_updated_at AFTER UPDATE ON technical_issues
BEGIN UPDATE technical_issues SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS notes_updated_at AFTER UPDATE ON notes
BEGIN UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS inventory_stock_updated_at AFTER UPDATE ON inventory_stock
BEGIN UPDATE inventory_stock SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS knowledge_articles_updated_at AFTER UPDATE ON knowledge_articles
BEGIN UPDATE knowledge_articles SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;
