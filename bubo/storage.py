import json
import logging
import time
from dataclasses import asdict
from importlib import import_module
from typing import Optional, List

import sqlite3
# noinspection PyPackageRequirements
from nio import MegolmEvent

latest_db_version = 10

logger = logging.getLogger(__name__)


class Storage(object):
    def __init__(self, db_path):
        """Set up the database

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

    def get_encrypted_events(self, session_id: str):
        results = self.cursor.execute("""
            select * from encrypted_events where session_id = ?;
        """, (session_id,))
        return results.fetchall()

    def get_recreate_room(self, room_id: str):
        results = self.cursor.execute("""
            select requester, timestamp, applied from recreate_rooms where room_id = ?;
        """, (room_id,))
        return results.fetchone()

    def get_room(self, room_id: str) -> Optional[sqlite3.Row]:
        results = self.cursor.execute("""
            select * from rooms where room_id = ?
        """, (room_id,))
        return results.fetchone()

    def get_room_by_alias(self, alias: str) -> Optional[sqlite3.Row]:
        if alias.startswith("#"):
            localpart = alias.split(":")[0].strip("#")
        else:
            localpart = alias
        results = self.cursor.execute("""
            select id, name, alias, room_id, title, icon, encrypted, public, type from rooms where alias = ?
        """, (localpart,))
        return results.fetchone()

    def get_room_id(self, alias: str) -> Optional[str]:
        results = self.cursor.execute("""
            select room_id from rooms where alias = ?
        """, (alias.split(":")[0].strip("#"),))
        room = results.fetchone()
        if room:
            return room[0]

    def get_rooms(self, spaces=False) -> List[sqlite3.Row]:
        query = "select * from rooms"
        if spaces:
            query = f"{query} where type = 'space'"
        results = self.cursor.execute(query)
        return results.fetchall()

    def remove_encrypted_event(self, event_id: str):
        self.cursor.execute("""
            delete from encrypted_events where event_id = ?;
        """, (event_id,))
        self.conn.commit()

    def set_recreate_room_applied(self, room_id: str):
        self.cursor.execute("""
            update recreate_rooms set applied = 1 where room_id = ?; 
        """, (room_id,))
        self.conn.commit()

    def set_room_alias(self, room_id: str, alias: str) -> None:
        self.cursor.execute("""
            update rooms set alias = ? where room_id = ?;
        """, (alias.split(":")[0].strip("#"), room_id))
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

    def store_encrypted_event(self, event: MegolmEvent):
        try:
            event_dict = asdict(event)
            event_json = json.dumps(event_dict)
            self.cursor.execute("""
                insert into encrypted_events
                    (device_id, event_id, room_id, session_id, event) values
                    (?, ?, ?, ?, ?)
            """, (event.device_id, event.event_id, event.room_id, event.session_id, event_json))
            self.conn.commit()
        except Exception as ex:
            logger.error("Failed to store encrypted event %s: %s" % (event.event_id, ex))

    def store_recreate_room(self, requester: str, room_id: str):
        timestamp = int(time.time())
        self.cursor.execute("""
            insert into recreate_rooms
                (requester, room_id, timestamp) values 
                (?, ?, ?);
        """, (requester, room_id, timestamp))
        self.conn.commit()

    def store_room(self, name, alias, room_id, title, encrypted, public, room_type):
        self.cursor.execute("""
            insert into rooms (
                name, alias, room_id, title, encrypted, public, type
            ) values (
                ?, ?, ?, ?, ?, ?, ?
            )
        """, (name, alias, room_id, title, encrypted, public, room_type))
        self.conn.commit()

    def unlink_room(self, room_id: str):
        self.cursor.execute("""
            delete from rooms where room_id = ?
        """, (room_id,))
        self.conn.commit()
