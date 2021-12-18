def forward(cursor):
    cursor.execute("""
        CREATE TABLE encrypted_events (
            id INTEGER PRIMARY KEY autoincrement,
            device_id text,
            event_id text unique,
            room_id text,
            session_id text,
            event text
        )
    """)
    cursor.execute("""
        CREATE INDEX encrypted_events_session_id_idx on encrypted_events (session_id);
    """)
