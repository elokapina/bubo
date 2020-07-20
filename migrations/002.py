def forward(cursor):
    cursor.execute("""
        CREATE TABLE rooms (
            id INTEGER PRIMARY KEY autoincrement,
            name text,
            alias text,
            room_id text null,
            title text default '',
            icon text default '',
            encrypted integer,
            public integer,
            power_to_write integer default 0
        )
    """)
    cursor.execute("""
        CREATE TABLE communities (
            id INTEGER PRIMARY KEY autoincrement,
            name text,
            alias text,
            title text default '',
            icon text default '',
            description text default ''
        )
    """)
    cursor.execute("""
        CREATE TABLE community_rooms (
            id INTEGER PRIMARY KEY autoincrement,
            room_id integer,
            community_id integer,
            constraint room_community_unique_idx unique (room_id, community_id)
        )
    """)

