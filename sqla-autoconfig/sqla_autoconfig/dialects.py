"""Database dialects and driver mappings for sqla-autoconfig."""

from dataclasses import dataclass
from typing import Dict, Optional
from sqla_autoconfig.exceptions import UnsupportedDialectError


@dataclass(frozen=True)
class DialectInfo:
    name: str
    default_sync_driver: str
    default_async_driver: str
    default_port: int
    url_scheme_base: str


class DialectRegistry:
    """Registry for database dialects and corresponding drivers."""

    _registry: Dict[str, DialectInfo] = {}

    @classmethod
    def register(
        cls,
        name: str,
        default_sync_driver: str,
        default_async_driver: str,
        default_port: int,
        url_scheme_base: Optional[str] = None
    ) -> None:
        key = name.lower()
        cls._registry[key] = DialectInfo(
            name=key,
            default_sync_driver=default_sync_driver,
            default_async_driver=default_async_driver,
            default_port=default_port,
            url_scheme_base=url_scheme_base or key
        )

    @classmethod
    def get(cls, name: str) -> DialectInfo:
        key = name.lower()
        # Aliases
        if key in ("postgresql", "pg"):
            key = "postgres"
        elif key in ("mariadb",):
            key = "mariadb"

        if key not in cls._registry:
            supported = list(cls._registry.keys())
            raise UnsupportedDialectError(
                f"Dialect '{name}' is not supported. Supported dialects: {supported}"
            )
        return cls._registry[key]

    @classmethod
    def is_supported(cls, name: str) -> bool:
        key = name.lower()
        if key in ("postgresql", "pg"):
            key = "postgres"
        return key in cls._registry

    @classmethod
    def list_supported(cls) -> list[str]:
        return list(cls._registry.keys())


# Register core default dialects
DialectRegistry.register(
    name="postgres",
    default_sync_driver="psycopg2",
    default_async_driver="asyncpg",
    default_port=5432,
    url_scheme_base="postgresql"
)

DialectRegistry.register(
    name="mysql",
    default_sync_driver="pymysql",
    default_async_driver="aiomysql",
    default_port=3306,
    url_scheme_base="mysql"
)

DialectRegistry.register(
    name="mariadb",
    default_sync_driver="pymysql",
    default_async_driver="aiomysql",
    default_port=3306,
    url_scheme_base="mysql"  # SQLAlchemy natively uses mysql+pymysql / mysql+aiomysql for MariaDB
)

DialectRegistry.register(
    name="sqlite",
    default_sync_driver="pysqlite",
    default_async_driver="aiosqlite",
    default_port=0,
    url_scheme_base="sqlite"
)
