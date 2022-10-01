def forward(cursor):
    cursor.execute("""
        DROP TABLE communities
    """)
