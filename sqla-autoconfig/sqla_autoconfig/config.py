"""Cascading Configuration Loader and Pydantic Settings for sqla-autoconfig."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from sqla_autoconfig.dialects import DialectRegistry
from sqla_autoconfig.exceptions import ConfigurationError, UnsupportedDialectError


class DatabaseSettings(BaseModel):
    """Strongly-typed database connection and pool settings."""

    db_type: str = Field(description="Database dialect (e.g. postgres, mysql, mariadb)")
    host: str = Field(default="localhost", description="Database server host")
    port: Optional[int] = Field(default=None, description="Database port")
    user: Optional[str] = Field(default=None, description="Username")
    password: str = Field(default="", description="Password")
    database: str = Field(default="test", description="Database name")
    url: Optional[str] = Field(default=None, description="Full SQLAlchemy connection URL override")
    driver: Optional[str] = Field(default=None, description="Explicit driver override")

    # Production-ready high-concurrency connection pool parameters
    pool_size: int = Field(default=20, ge=1, le=1000, description="Base pool size")
    max_overflow: int = Field(default=10, ge=0, le=1000, description="Max overflow connections")
    pool_recycle: int = Field(default=1800, ge=1, description="Connection recycle interval in seconds")
    pool_pre_ping: bool = Field(default=True, description="Enable pre-ping test to discard dead connections")
    pool_timeout: float = Field(default=30.0, gt=0, description="Pool checkout timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements to stdout/logs")

    @field_validator("db_type")
    @classmethod
    def validate_dialect(cls, v: str) -> str:
        dialect_name = v.lower()
        if dialect_name in ("postgresql", "pg"):
            dialect_name = "postgres"
        if not DialectRegistry.is_supported(dialect_name):
            raise UnsupportedDialectError(
                f"Dialect '{v}' is not supported. Supported dialects: {DialectRegistry.list_supported()}"
            )
        return dialect_name

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 65535):
            raise ConfigurationError(f"Port must be between 1 and 65535, got {v}")
        return v

    @model_validator(mode="after")
    def populate_defaults(self) -> "DatabaseSettings":
        # Default port based on dialect if not explicitly specified
        if self.port is None:
            dialect_info = DialectRegistry.get(self.db_type)
            self.port = dialect_info.default_port

        # Default user based on dialect if not specified
        if self.user is None:
            if self.db_type == "postgres":
                self.user = "postgres"
            else:
                self.user = "root"
        return self

    def build_url(self, async_mode: bool = False) -> str:
        """Construct a SQLAlchemy connection URL with appropriate driver and safely escaped credentials."""
        if self.url:
            return self.url

        dialect_info = DialectRegistry.get(self.db_type)
        scheme_base = dialect_info.url_scheme_base

        if self.driver:
            driver = self.driver
        else:
            driver = dialect_info.default_async_driver if async_mode else dialect_info.default_sync_driver

        scheme = f"{scheme_base}+{driver}" if driver else scheme_base

        # Safely quote username and password to protect special characters like @, :, /, #
        safe_user = quote_plus(self.user) if self.user else ""
        safe_password = quote_plus(self.password) if self.password else ""

        auth_part = f"{safe_user}:{safe_password}@" if safe_user or safe_password else ""
        return f"{scheme}://{auth_part}{self.host}:{self.port}/{self.database}"


class ConfigLoader:
    """Cascading configuration loader with hierarchical precedence.
    
    Precedence Order:
    1. Explicit kwargs passed to constructor / load_cascading
    2. Environment Variables (DB_* or SQLA_*)
    3. YAML file (database.yaml, database.yml, config.yaml, application.yml)
    4. JSON file (database.json, config.json, application.json)
    5. Hardcoded Defaults
    """

    DEFAULT_JSON_FILES = ["database.json", "config.json", "application.json"]
    DEFAULT_YAML_FILES = ["database.yaml", "database.yml", "config.yaml", "application.yml"]

    ENV_MAPPING = {
        "DB_TYPE": "db_type",
        "SQLA_DB_TYPE": "db_type",
        "DB_HOST": "host",
        "SQLA_HOST": "host",
        "DB_PORT": "port",
        "SQLA_PORT": "port",
        "DB_USER": "user",
        "SQLA_USER": "user",
        "DB_PASSWORD": "password",
        "SQLA_PASSWORD": "password",
        "DB_NAME": "database",
        "SQLA_DATABASE": "database",
        "DATABASE_URL": "url",
        "SQLA_DATABASE_URL": "url",
        "DB_DRIVER": "driver",
        "SQLA_DRIVER": "driver",
        "DB_POOL_SIZE": "pool_size",
        "SQLA_POOL_SIZE": "pool_size",
        "DB_MAX_OVERFLOW": "max_overflow",
        "SQLA_MAX_OVERFLOW": "max_overflow",
        "DB_POOL_RECYCLE": "pool_recycle",
        "SQLA_POOL_RECYCLE": "pool_recycle",
        "DB_POOL_PRE_PING": "pool_pre_ping",
        "SQLA_POOL_PRE_PING": "pool_pre_ping",
        "DB_POOL_TIMEOUT": "pool_timeout",
        "SQLA_POOL_TIMEOUT": "pool_timeout",
        "DB_ECHO": "echo",
        "SQLA_ECHO": "echo",
    }

    INT_FIELDS = {"port", "pool_size", "max_overflow", "pool_recycle"}
    FLOAT_FIELDS = {"pool_timeout"}
    BOOL_FIELDS = {"pool_pre_ping", "echo"}

    def __init__(self, search_paths: Optional[List[str]] = None):
        self.search_paths = [Path(p) for p in (search_paths or [os.getcwd()])]

    def find_file(self, filenames: List[str]) -> Optional[Path]:
        for base_path in self.search_paths:
            for fname in filenames:
                candidate = base_path / fname
                if candidate.is_file():
                    return candidate
        return None

    @staticmethod
    def _normalize_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize hierarchical (nested) or flat config dictionaries into flat DatabaseSettings fields."""
        normalized: Dict[str, Any] = {}

        # 1. Check for root namespace: 'database', 'sqla', 'db'
        root_data = raw
        for ns in ("database", "sqla", "db"):
            if ns in raw and isinstance(raw[ns], dict):
                root_data = raw[ns]
                break

        # 2. Extract db_type / type / dialect
        for key in ("db_type", "type", "dialect"):
            if key in root_data:
                normalized["db_type"] = root_data[key]
                break

        # 3. Extract connection fields (from root_data['connection'] or root_data)
        conn_data = root_data.get("connection", {}) if isinstance(root_data.get("connection"), dict) else {}

        if "host" in conn_data:
            normalized["host"] = conn_data["host"]
        elif "host" in root_data:
            normalized["host"] = root_data["host"]

        if "port" in conn_data:
            normalized["port"] = conn_data["port"]
        elif "port" in root_data:
            normalized["port"] = root_data["port"]

        for u_key in ("user", "username"):
            if u_key in conn_data:
                normalized["user"] = conn_data[u_key]
                break
            elif u_key in root_data:
                normalized["user"] = root_data[u_key]
                break

        if "password" in conn_data:
            normalized["password"] = conn_data["password"]
        elif "password" in root_data:
            normalized["password"] = root_data["password"]

        for db_key in ("database", "name", "dbname"):
            if db_key in conn_data:
                normalized["database"] = conn_data[db_key]
                break
            elif db_key in root_data and isinstance(root_data[db_key], str):
                normalized["database"] = root_data[db_key]
                break

        if "url" in conn_data:
            normalized["url"] = conn_data["url"]
        elif "url" in root_data:
            normalized["url"] = root_data["url"]

        if "driver" in conn_data:
            normalized["driver"] = conn_data["driver"]
        elif "driver" in root_data:
            normalized["driver"] = root_data["driver"]

        # 4. Extract pool fields (from root_data['pool'] or root_data)
        pool_data = root_data.get("pool", {}) if isinstance(root_data.get("pool"), dict) else {}

        for s_key in ("pool_size", "size"):
            if s_key in pool_data:
                normalized["pool_size"] = pool_data[s_key]
                break
            elif s_key in root_data and isinstance(root_data[s_key], (int, str)):
                normalized["pool_size"] = root_data[s_key]
                break

        for o_key in ("max_overflow", "overflow"):
            if o_key in pool_data:
                normalized["max_overflow"] = pool_data[o_key]
                break
            elif o_key in root_data and isinstance(root_data[o_key], (int, str)):
                normalized["max_overflow"] = root_data[o_key]
                break

        for r_key in ("pool_recycle", "recycle"):
            if r_key in pool_data:
                normalized["pool_recycle"] = pool_data[r_key]
                break
            elif r_key in root_data and isinstance(root_data[r_key], (int, str)):
                normalized["pool_recycle"] = root_data[r_key]
                break

        for p_key in ("pool_pre_ping", "pre_ping"):
            if p_key in pool_data:
                normalized["pool_pre_ping"] = pool_data[p_key]
                break
            elif p_key in root_data and isinstance(root_data[p_key], (bool, str)):
                normalized["pool_pre_ping"] = root_data[p_key]
                break

        for t_key in ("pool_timeout", "timeout"):
            if t_key in pool_data:
                normalized["pool_timeout"] = pool_data[t_key]
                break
            elif t_key in root_data and isinstance(root_data[t_key], (int, float, str)):
                normalized["pool_timeout"] = root_data[t_key]
                break

        # 5. Extract echo
        if "echo" in root_data and isinstance(root_data["echo"], (bool, str)):
            normalized["echo"] = root_data["echo"]

        return normalized

    def load_from_json(self, file_path: Path) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._normalize_dict(data) if isinstance(data, dict) else {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load JSON config from {file_path}: {e}") from e

    def load_from_yaml(self, file_path: Path) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return self._normalize_dict(data) if isinstance(data, dict) else {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load YAML config from {file_path}: {e}") from e

    def load_from_env(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for env_var, field_name in self.ENV_MAPPING.items():
            if env_var in os.environ:
                raw_val = os.environ[env_var]
                if field_name in self.INT_FIELDS:
                    try:
                        result[field_name] = int(raw_val)
                    except ValueError:
                        raise ConfigurationError(f"Environment variable {env_var} must be an integer, got '{raw_val}'")
                elif field_name in self.FLOAT_FIELDS:
                    try:
                        result[field_name] = float(raw_val)
                    except ValueError:
                        raise ConfigurationError(f"Environment variable {env_var} must be a float, got '{raw_val}'")
                elif field_name in self.BOOL_FIELDS:
                    result[field_name] = raw_val.strip().lower() in ("true", "1", "yes", "on")
                else:
                    result[field_name] = raw_val
        return result

    def load_cascading(
        self,
        filenames_override: Optional[Dict[str, List[str]]] = None,
        **explicit_kwargs: Any
    ) -> DatabaseSettings:
        merged: Dict[str, Any] = {}

        # 1. JSON file (lowest file precedence)
        if filenames_override is not None:
            json_targets = filenames_override.get("json", [])
        else:
            json_targets = self.DEFAULT_JSON_FILES

        if json_targets:
            json_path = self.find_file(json_targets)
            if json_path:
                merged.update(self.load_from_json(json_path))

        # 2. YAML file (overrides JSON)
        if filenames_override is not None:
            yaml_targets = filenames_override.get("yaml", [])
        else:
            yaml_targets = self.DEFAULT_YAML_FILES

        if yaml_targets:
            yaml_path = self.find_file(yaml_targets)
            if yaml_path:
                merged.update(self.load_from_yaml(yaml_path))

        # 3. Environment variables (overrides files)
        merged.update(self.load_from_env())

        # 4. Explicit keyword arguments (highest precedence)
        for k, v in explicit_kwargs.items():
            if v is not None:
                merged[k] = v

        if not merged.get("db_type") and not merged.get("url"):
            # Default to postgres if none specified
            merged["db_type"] = "postgres"

        try:
            return DatabaseSettings(**merged)
        except (ConfigurationError, UnsupportedDialectError):
            raise
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}") from e
