_toner_counter_v1 = '''
CREATE TABLE IF NOT EXISTS toner_counter (
    id INTEGER PRIMARY KEY, -- Menjadi ROWID eksplisit
    inserted_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), -- Otomatis terisi waktu saat ini
    inserted_by TEXT NOT NULL,
    condition TEXT NOT NULL DEFAULT 'NEW',
    counter_type TEXT NOT NULL CHECK (counter_type IN ('BW', 'FULLCOLOR')),
    counter_value INTEGER NOT NULL
);'''
_schema_v1 = [_toner_counter_v1]

schemas = [_schema_v1]