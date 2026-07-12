_toner_counter_v1 = '''
CREATE TABLE IF NOT EXISTS toner_counter (
    id INTEGER PRIMARY KEY, -- Menjadi ROWID eksplisit
    inserted_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), -- Otomatis terisi waktu saat ini
    inserted_by TEXT NOT NULL,
    color TEXT NOT NULL,
    condition TEXT NOT NULL DEFAULT 'NEW',
    counter_type TEXT NOT NULL CHECK (counter_type IN ('BW', 'FULLCOLOR')),
    counter_value INTEGER NOT NULL
);'''

_part_replacement_log_v1 = '''
CREATE TABLE IF NOT EXISTS a3_part_replacement (
    id INTEGER PRIMARY KEY,
    part_name TEXT NOT NULL COLLATE NOCASE,
    install_date TEXT NOT NULL,
    installer TEXT NOT NULL,
    counter_fullcolor_value INT NOT NULL,
    description TEXT NOT NULL DEFAULT '{}' CHECK ( json_valid(description) = 1)
);
'''

_schema_v1 = [_toner_counter_v1, _part_replacement_log_v1]
_schema_v2 = [_part_replacement_log_v1]

schemas = [_schema_v1, _schema_v2]