def forward(cursor):
    cursor.execute("""
        ALTER TABLE rooms
            ADD type text default ''
    """)
