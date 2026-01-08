"""
Database Connection Manager for Chat with Data.

Manages connections to external databases (PostgreSQL, MySQL, SQLite)
with connection pooling, secure credential storage, and read-only enforcement.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from dbnotebook.core.sql_chat.types import (
    DatabaseConnection,
    DatabaseType,
    MaskingPolicy,
    SchemaInfo,
)
from dbnotebook.core.sql_chat.validators import QueryValidator

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """Manage external database connections with pooling.

    Provides secure connection management for PostgreSQL, MySQL, and SQLite
    databases with:
    - Connection pooling via SQLAlchemy
    - Encrypted credential storage
    - Read-only access enforcement
    - Connection health monitoring
    """

    # Database driver mappings
    SUPPORTED_DRIVERS: Dict[str, str] = {
        'postgresql': 'postgresql+psycopg2',
        'mysql': 'mysql+pymysql',
        'sqlite': 'sqlite',
    }

    # Default ports for each database type
    DEFAULT_PORTS: Dict[str, int] = {
        'postgresql': 5432,
        'mysql': 3306,
        'sqlite': 0,  # N/A for SQLite
    }

    def __init__(
        self,
        db_manager=None,
        encryption_key: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30
    ):
        """Initialize connection manager.

        Args:
            db_manager: Database manager for persisting connections to DBNotebook DB
            encryption_key: Fernet encryption key for passwords.
                           Falls back to SQL_CHAT_ENCRYPTION_KEY env var.
            pool_size: Connection pool size per database
            max_overflow: Max connections beyond pool_size
            pool_timeout: Seconds to wait for available connection
        """
        self._db_manager = db_manager  # For persisting connections
        self._engines: Dict[str, Engine] = {}
        self._connections: Dict[str, DatabaseConnection] = {}
        self._validator = QueryValidator()

        # Pool configuration
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_timeout = pool_timeout

        # Initialize encryption with default key for dev (or custom for production)
        # Default key allows persistence without configuration
        DEFAULT_DEV_KEY = "ZmFrZS1kZXYta2V5LWZvci10ZXN0aW5nLW9ubHk9PT0="  # Base64 padded
        key = encryption_key or os.getenv("SQL_CHAT_ENCRYPTION_KEY") or DEFAULT_DEV_KEY

        # Generate a proper Fernet key from the provided/default key
        import hashlib
        import base64
        key_bytes = hashlib.sha256(key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        self._fernet = Fernet(fernet_key)

        # Load existing connections from database
        if self._db_manager:
            self._load_connections_from_db()

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password using Fernet encryption.

        Args:
            password: Plain text password

        Returns:
            Encrypted password string
        """
        return self._fernet.encrypt(password.encode()).decode()

    def _decrypt_password(self, encrypted: str) -> str:
        """Decrypt password using Fernet encryption.

        Args:
            encrypted: Encrypted password string

        Returns:
            Plain text password
        """
        return self._fernet.decrypt(encrypted.encode()).decode()

    def _load_connections_from_db(self) -> None:
        """Load all connections from database on startup."""
        if not self._db_manager:
            return

        try:
            with self._db_manager.get_session() as session:
                result = session.execute(text("""
                    SELECT id, user_id, name, db_type, host, port, database_name,
                           username, password_encrypted, masking_policy
                    FROM database_connections
                """))
                rows = result.fetchall()

                for row in rows:
                    conn_id = str(row.id)
                    masking_policy = None
                    if row.masking_policy:
                        import json
                        policy_data = row.masking_policy if isinstance(row.masking_policy, dict) else json.loads(row.masking_policy)
                        masking_policy = MaskingPolicy(
                            mask_columns=policy_data.get('mask_columns', []),
                            redact_columns=policy_data.get('redact_columns', []),
                            hash_columns=policy_data.get('hash_columns', []),
                        )

                    config = DatabaseConnection(
                        id=conn_id,
                        name=row.name,
                        type=row.db_type,
                        host=row.host or '',
                        port=row.port or 0,
                        database=row.database_name or '',
                        username=row.username or '',
                        password_encrypted=row.password_encrypted,
                        masking_policy=masking_policy,
                        user_id=row.user_id,
                    )
                    self._connections[conn_id] = config

                    # Try to establish engine (may fail if credentials changed)
                    try:
                        password = self._decrypt_password(row.password_encrypted)
                        engine = self._create_engine(config, password)
                        self._engines[conn_id] = engine
                    except Exception as e:
                        logger.warning(f"Failed to create engine for connection {conn_id}: {e}")

                logger.info(f"Loaded {len(rows)} database connections from storage")

        except Exception as e:
            logger.error(f"Failed to load connections from database: {e}")

    def _save_connection_to_db(self, config: DatabaseConnection) -> bool:
        """Save connection to database.

        Args:
            config: Connection configuration to save

        Returns:
            True if saved successfully
        """
        if not self._db_manager:
            logger.warning("No db_manager - connection will not persist across restarts")
            return False

        try:
            with self._db_manager.get_session() as session:
                # Convert masking policy to JSON
                masking_json = None
                if config.masking_policy:
                    import json
                    masking_json = json.dumps({
                        'mask_columns': config.masking_policy.mask_columns,
                        'redact_columns': config.masking_policy.redact_columns,
                        'hash_columns': config.masking_policy.hash_columns,
                    })

                session.execute(text("""
                    INSERT INTO database_connections
                    (id, user_id, name, db_type, host, port, database_name,
                     username, password_encrypted, masking_policy)
                    VALUES (CAST(:id AS uuid), :user_id, :name, :db_type, :host, :port,
                            :database_name, :username, :password_encrypted,
                            CAST(:masking_policy AS jsonb))
                """), {
                    'id': config.id,
                    'user_id': config.user_id,
                    'name': config.name,
                    'db_type': config.type,
                    'host': config.host,
                    'port': config.port,
                    'database_name': config.database,
                    'username': config.username,
                    'password_encrypted': config.password_encrypted,
                    'masking_policy': masking_json,
                })
                session.commit()
                logger.info(f"Saved connection {config.id} to database")
                return True

        except Exception as e:
            logger.error(f"Failed to save connection to database: {e}")
            return False

    def _delete_connection_from_db(self, connection_id: str) -> bool:
        """Delete connection from database.

        Args:
            connection_id: Connection ID to delete

        Returns:
            True if deleted successfully
        """
        if not self._db_manager:
            return False

        try:
            with self._db_manager.get_session() as session:
                session.execute(text("""
                    DELETE FROM database_connections WHERE id = CAST(:id AS uuid)
                """), {'id': connection_id})
                session.commit()
                logger.info(f"Deleted connection {connection_id} from database")
                return True

        except Exception as e:
            logger.error(f"Failed to delete connection from database: {e}")
            return False

    def _update_last_used(self, connection_id: str) -> None:
        """Update last_used_at timestamp for a connection.

        Args:
            connection_id: Connection ID
        """
        if not self._db_manager:
            return

        try:
            with self._db_manager.get_session() as session:
                session.execute(text("""
                    UPDATE database_connections
                    SET last_used_at = NOW()
                    WHERE id = CAST(:id AS uuid)
                """), {'id': connection_id})
                session.commit()
        except Exception as e:
            logger.debug(f"Failed to update last_used_at: {e}")

    def _build_connection_uri(
        self,
        db_type: DatabaseType,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str
    ) -> str:
        """Build SQLAlchemy connection URI.

        Args:
            db_type: Database type
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password (plain text)

        Returns:
            SQLAlchemy connection URI
        """
        driver = self.SUPPORTED_DRIVERS.get(db_type)
        if not driver:
            raise ValueError(f"Unsupported database type: {db_type}")

        if db_type == "sqlite":
            return f"sqlite:///{database}"

        # URL-encode password to handle special characters
        encoded_password = quote_plus(password)
        return f"{driver}://{username}:{encoded_password}@{host}:{port}/{database}"

    def _create_engine(
        self,
        config: DatabaseConnection,
        password: str
    ) -> Engine:
        """Create SQLAlchemy engine with connection pool.

        Args:
            config: Database connection configuration
            password: Decrypted password

        Returns:
            SQLAlchemy Engine instance
        """
        uri = self._build_connection_uri(
            db_type=config.type,
            host=config.host,
            port=config.port,
            database=config.database,
            username=config.username,
            password=password
        )

        # Pool configuration (not applicable to SQLite)
        if config.type == "sqlite":
            return create_engine(uri)

        return create_engine(
            uri,
            poolclass=QueuePool,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            pool_timeout=self._pool_timeout,
            pool_pre_ping=True,  # Verify connections before use
        )

    def create_connection(
        self,
        user_id: str,
        name: str,
        db_type: DatabaseType,
        host: str,
        database: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        masking_policy: Optional[MaskingPolicy] = None
    ) -> Tuple[str, Optional[str]]:
        """Create and store a new database connection.

        Args:
            user_id: User ID who owns this connection
            name: Display name for connection
            db_type: Database type
            host: Database host
            database: Database name
            username: Database username
            password: Database password (will be encrypted)
            port: Database port (uses default if not specified)
            masking_policy: Optional data masking configuration

        Returns:
            Tuple of (connection_id, error_message)
        """
        # Use default port if not specified
        if port is None:
            port = self.DEFAULT_PORTS.get(db_type, 5432)

        connection_id = str(uuid.uuid4())

        # Create connection config
        config = DatabaseConnection(
            id=connection_id,
            name=name,
            type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
            password_encrypted=self._encrypt_password(password),
            masking_policy=masking_policy,
            user_id=user_id,
        )

        # Test connection before storing
        success, error = self.test_connection_config(config, password)
        if not success:
            return "", error

        # Store connection
        try:
            engine = self._create_engine(config, password)
            self._engines[connection_id] = engine
            self._connections[connection_id] = config

            # Persist to database for cross-session persistence
            self._save_connection_to_db(config)

            logger.info(f"Created connection {connection_id} for user {user_id}")
            return connection_id, None
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return "", str(e)

    def test_connection_config(
        self,
        config: DatabaseConnection,
        password: str
    ) -> Tuple[bool, str]:
        """Test database connection AND verify read-only access.

        Args:
            config: Connection configuration
            password: Plain text password

        Returns:
            Tuple of (success, message)
        """
        try:
            engine = self._create_engine(config, password)

            # Test 1: Can connect and run basic query
            with engine.connect() as conn:
                test_sql = self._validator.validate_connection_test_sql(config.type)
                conn.execute(text(test_sql))
                logger.debug(f"Connection test passed for {config.name}")

            # Check if we should skip read-only verification (dev mode)
            skip_readonly_check = os.getenv("SQL_CHAT_SKIP_READONLY_CHECK", "false").lower() == "true"

            if skip_readonly_check:
                logger.info(f"Skipping read-only check for {config.name} (dev mode)")
                return True, "Connection successful (read-only check skipped - dev mode)"

            # Test 2: Verify read-only (write should FAIL)
            with engine.connect() as conn:
                try:
                    write_test_sql = self._validator.get_read_only_test_sql(config.type)
                    conn.execute(text(write_test_sql))
                    # If we get here, user has write access - this is bad
                    # Try to clean up the test table
                    try:
                        conn.execute(text("DROP TABLE __test_readonly_check"))
                        conn.commit()
                    except Exception:
                        pass
                    logger.warning(f"Connection {config.name} has write access!")
                    return False, (
                        "ERROR: Database user has write access. "
                        "Please use a read-only database user for security."
                    )
                except Exception:
                    # Good - write failed, user is read-only
                    pass

            return True, "Connection successful (read-only verified)"

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False, f"Connection failed: {str(e)}"

    def test_connection(
        self,
        db_type: DatabaseType,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str
    ) -> Tuple[bool, str]:
        """Test connection with provided credentials.

        Convenience method for testing before creating connection.

        Args:
            db_type: Database type
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password

        Returns:
            Tuple of (success, message)
        """
        temp_config = DatabaseConnection(
            id="temp",
            name="temp",
            type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
        )
        return self.test_connection_config(temp_config, password)

    def connect(self, connection_id: str) -> bool:
        """Verify connection is active and reconnect if needed.

        Args:
            connection_id: ID of connection to verify

        Returns:
            True if connection is active
        """
        if connection_id not in self._engines:
            return False

        engine = self._engines[connection_id]
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"Connection {connection_id} unhealthy: {e}")
            return False

    def disconnect(self, connection_id: str, delete_from_db: bool = True) -> None:
        """Close and remove a database connection.

        Args:
            connection_id: ID of connection to close
            delete_from_db: If True, also delete from database (default True)
        """
        if connection_id in self._engines:
            self._engines[connection_id].dispose()
            del self._engines[connection_id]
            logger.info(f"Disconnected {connection_id}")

        if connection_id in self._connections:
            del self._connections[connection_id]

        # Delete from database if requested
        if delete_from_db:
            self._delete_connection_from_db(connection_id)

    def get_engine(self, connection_id: str) -> Optional[Engine]:
        """Get SQLAlchemy engine for connection.

        Args:
            connection_id: Connection ID

        Returns:
            Engine instance or None if not found
        """
        return self._engines.get(connection_id)

    def get_connection(self, connection_id: str) -> Optional[DatabaseConnection]:
        """Get connection configuration.

        Args:
            connection_id: Connection ID

        Returns:
            DatabaseConnection or None if not found
        """
        return self._connections.get(connection_id)

    def list_connections(self, user_id: str) -> List[DatabaseConnection]:
        """List all connections for a user.

        Args:
            user_id: User ID

        Returns:
            List of DatabaseConnection instances
        """
        return [
            conn for conn in self._connections.values()
            if conn.user_id == user_id
        ]

    def get_default_port(self, db_type: DatabaseType) -> int:
        """Get default port for database type.

        Args:
            db_type: Database type

        Returns:
            Default port number
        """
        return self.DEFAULT_PORTS.get(db_type, 5432)

    def parse_connection_string(self, connection_string: str) -> Tuple[Optional[dict], str]:
        """Parse connection string into components.

        Supports formats like:
        - postgresql://user:pass@host:port/database
        - mysql+pymysql://user:pass@host:port/database
        - sqlite:///path/to/db.sqlite

        Args:
            connection_string: Connection string to parse

        Returns:
            Tuple of (parsed_config dict, error_message)
        """
        try:
            from urllib.parse import urlparse

            parsed = urlparse(connection_string)

            # Determine database type from scheme
            scheme = parsed.scheme.lower()
            if 'postgresql' in scheme or 'postgres' in scheme:
                db_type = 'postgresql'
            elif 'mysql' in scheme:
                db_type = 'mysql'
            elif 'sqlite' in scheme:
                db_type = 'sqlite'
            else:
                return None, f"Unsupported database type in connection string: {scheme}"

            if db_type == 'sqlite':
                return {
                    'type': db_type,
                    'database': parsed.path,
                    'host': '',
                    'port': 0,
                    'username': '',
                    'password': '',
                }, ""

            return {
                'type': db_type,
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or self.DEFAULT_PORTS[db_type],
                'database': parsed.path.lstrip('/'),
                'username': parsed.username or '',
                'password': parsed.password or '',
            }, ""

        except Exception as e:
            return None, f"Failed to parse connection string: {str(e)}"

    def close_all(self) -> None:
        """Close all connections. Call on shutdown."""
        for conn_id in list(self._engines.keys()):
            self.disconnect(conn_id)
        logger.info("All database connections closed")
