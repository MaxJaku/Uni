CREATE TABLE IF NOT EXISTS user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS customer (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_number TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  address TEXT,
  phone TEXT,
  email TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS asset (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL,
  asset_number TEXT NOT NULL UNIQUE,
  location TEXT,
  asset_type TEXT,
  manufacturer TEXT,
  model TEXT,
  commissioning_date TEXT,
  maintenance_interval_months INTEGER NOT NULL DEFAULT 3,
  last_regular_maintenance_at TEXT,
  next_maintenance_at TEXT,
  status TEXT NOT NULL DEFAULT 'aktiv',
  FOREIGN KEY (customer_id) REFERENCES customer(id)
);

CREATE TABLE IF NOT EXISTS planned_maintenance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  due_date TEXT NOT NULL,
  status TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  FOREIGN KEY (asset_id) REFERENCES asset(id),
  FOREIGN KEY (customer_id) REFERENCES customer(id)
);

CREATE TABLE IF NOT EXISTS maintenance_protocol (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  planned_maintenance_id INTEGER,
  user_id INTEGER NOT NULL,
  protocol_date TEXT NOT NULL,
  protocol_type TEXT NOT NULL,
  counts_as_regular INTEGER NOT NULL DEFAULT 0,
  checklist TEXT,
  measurements TEXT,
  findings TEXT,
  defects TEXT,
  recommendation TEXT,
  completion_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (asset_id) REFERENCES asset(id),
  FOREIGN KEY (customer_id) REFERENCES customer(id),
  FOREIGN KEY (planned_maintenance_id) REFERENCES planned_maintenance(id),
  FOREIGN KEY (user_id) REFERENCES user(id)
);
