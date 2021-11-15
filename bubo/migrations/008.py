def forward(cursor):
    cursor.execute("""
        CREATE TABLE recreate_rooms (
            id INTEGER PRIMARY KEY autoincrement,
            requester text,
            room_id text,
            timestamp integer,
            applied integer default 0
        )
    """)
