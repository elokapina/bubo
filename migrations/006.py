def forward(cursor):
    cursor.execute("""
        CREATE TABLE breakout_rooms (
            id INTEGER PRIMARY KEY autoincrement,
            event_id text,
            room_id text
        )
    """)
