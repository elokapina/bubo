def forward(cursor):
    # sync_token table
    cursor.execute("""
        CREATE TABLE sync_token (
            dedupe_id INTEGER PRIMARY KEY, 
            token TEXT NOT NULL
        )
    """)
