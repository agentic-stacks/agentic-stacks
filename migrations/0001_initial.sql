-- migrations/0001_initial.sql
CREATE TABLE IF NOT EXISTS namespaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    github_org TEXT,
    verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace_id INTEGER NOT NULL REFERENCES namespaces(id),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stack_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stack_id INTEGER NOT NULL REFERENCES stacks(id),
    version TEXT NOT NULL,
    target_software TEXT DEFAULT '',
    target_versions TEXT DEFAULT '[]',
    skills TEXT DEFAULT '[]',
    profiles TEXT DEFAULT '{}',
    depends_on TEXT DEFAULT '[]',
    deprecations TEXT DEFAULT '[]',
    requires TEXT DEFAULT '{}',
    digest TEXT NOT NULL,
    registry_ref TEXT NOT NULL,
    published_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_namespaces_name ON namespaces(name);
CREATE INDEX IF NOT EXISTS idx_stacks_name ON stacks(name);
CREATE INDEX IF NOT EXISTS idx_stacks_namespace ON stacks(namespace_id);
CREATE INDEX IF NOT EXISTS idx_versions_stack ON stack_versions(stack_id);
