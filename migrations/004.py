def forward(cursor):
    cursor.execute("""
        CREATE TABLE communities_backup (
            id INTEGER PRIMARY KEY,
            name text,
            alias text,
            title text default '',
            icon text default '',
            description text default ''
        )
    """)
    cursor.execute("""
        INSERT INTO communities_backup SELECT id, name, alias, title, icon, description 
            FROM communities
    """)
    cursor.execute("""
        DROP TABLE communities
    """)
    cursor.execute("""
        CREATE TABLE communities (
            id INTEGER PRIMARY KEY autoincrement,
            name text,
            alias text constraint community_alias_unique_idx unique,
            title text default '',
            icon text default '',
            description text default ''
        )
    """)
    cursor.execute("""
        INSERT INTO communities SELECT id, name, alias, title, icon, description 
            FROM communities_backup
    """)
    cursor.execute("""
        DROP TABLE communities_backup
    """)
