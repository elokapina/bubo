import logging
import time
from importlib import import_module
from typing import Optional, List

import sqlite3

latest_db_version = 8

logger = logging.getLogger(__name__)


class Storage(object):
    def __init__(self, db_path):
        """Setup the database

        Runs an initial setup or migrations depending on whether a database file has already
        been created

        Args:
            db_path (str): The name of the database file
        """
        self.db_path = db_path

        self._initial_setup()
        self._run_migrations()

    def _initial_setup(self):
        """Initial setup of the database"""
        logger.info("Performing initial database setup...")

        # Initialize a connection to the database
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Create database_version table if it doesn't exist
        try:
            self.cursor.execute("""
                CREATE TABLE database_version (version INTEGER)
            """)
            self.cursor.execute("""
                insert into database_version (version) values (0)
            """)
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

        logger.info("Database setup complete")

    def _run_migrations(self):
        """Execute database migrations"""
        # Get current version of db
        results = self.cursor.execute("select version from database_version")
        version = results.fetchone()[0]
        if version >= latest_db_version:
            logger.info("No migrations to run")
            return

        while version < latest_db_version:
            version += 1
            version_string = str(version).rjust(3, "0")
            migration = import_module(f"bubo.migrations.{version_string}")
            # noinspection PyUnresolvedReferences
            migration.forward(self.cursor)
            logger.info(f"Executing database migration {version_string}")
            # noinspection SqlWithoutWhere
            self.cursor.execute("update database_version set version = ?", (version_string,))
            self.conn.commit()
            logger.info(f"...done")

    def delete_recreate_room(self, room_id: str):
        self.cursor.execute("""
            delete from recreate_rooms where room_id = ?;
        """, (room_id,))
        self.conn.commit()

    def get_breakout_room_id(self, event_id: str):
        results = self.cursor.execute("""
            select room_id from breakout_rooms where event_id = ?;
        """, (event_id,))
        room = results.fetchone()
        if room:
            return room[0]

    def get_recreate_room(self, room_id: str):
        results = self.cursor.execute("""
            select requester, timestamp, applied from recreate_rooms where room_id = ?;
        """, (room_id,))
        return results.fetchone()

    def get_room_id(self, alias: str) -> Optional[str]:
        results = self.cursor.execute("""
            select room_id from rooms where alias = ?
        """, (alias.split(":")[0].strip("#"),))
        room = results.fetchone()
        if room:
            return room[0]

    def get_rooms(self) -> List[sqlite3.Row]:
        results = self.cursor.execute("""
            select * from rooms
        """)
        return results.fetchall()

    def set_recreate_room_applied(self, room_id: str):
        self.cursor.execute("""
            update recreate_rooms set applied = 1 where room_id = ?; 
        """, (room_id,))
        self.conn.commit()

    def set_room_id(self, alias: str, room_id: str) -> None:
        self.cursor.execute("""
            update rooms set room_id = ? where alias = ?;
        """, (room_id, alias.split(":")[0].strip("#")))
        self.conn.commit()

    def store_breakout_room(self, event_id: str, room_id: str):
        self.cursor.execute("""
            insert into breakout_rooms
                (event_id, room_id) values 
                (?, ?);
        """, (event_id, room_id))
        self.conn.commit()

    def store_community(self, name: str, alias: str, title: str):
        self.cursor.execute("""
            insert into communities
                (name, alias, title) values 
                (?, ?, ?);
        """, (name, alias, title))
        self.conn.commit()

    def store_recreate_room(self, requester: str, room_id: str):
        timestamp = int(time.time())
        self.cursor.execute("""
            insert into recreate_rooms
                (requester, room_id, timestamp) values 
                (?, ?, ?);
        """, (requester, room_id, timestamp))
        self.conn.commit()
