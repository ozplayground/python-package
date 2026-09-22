import pytest
from sqla_autoconfig.dialects import DialectRegistry
from sqla_autoconfig.config import DatabaseSettings
from sqla_autoconfig.exceptions import UnsupportedDialectError


def test_core_dialects_mapping():
    """PostgreSQL, MySQL, MariaDB 드라이버 및 포트 매핑 검증"""
    pg = DialectRegistry.get("postgres")
    assert pg.default_sync_driver == "psycopg2"
    assert pg.default_async_driver == "asyncpg"
    assert pg.default_port == 5432

    mysql = DialectRegistry.get("mysql")
    assert mysql.default_sync_driver == "pymysql"
    assert mysql.default_async_driver == "aiomysql"
    assert mysql.default_port == 3306

    mariadb = DialectRegistry.get("mariadb")
    assert mariadb.default_sync_driver == "pymysql"
    assert mariadb.default_async_driver == "aiomysql"
    assert mariadb.default_port == 3306


def test_url_scheme_generation():
    """동기 및 비동기 URL 스킴 조합 검증"""
    pg_settings = DatabaseSettings(db_type="postgres", database="mydb", user="u", password="p")
    assert pg_settings.build_url(async_mode=False) == "postgresql+psycopg2://u:p@localhost:5432/mydb"
    assert pg_settings.build_url(async_mode=True) == "postgresql+asyncpg://u:p@localhost:5432/mydb"

    mysql_settings = DatabaseSettings(db_type="mysql", database="mydb", user="u", password="p")
    assert mysql_settings.build_url(async_mode=False) == "mysql+pymysql://u:p@localhost:3306/mydb"
    assert mysql_settings.build_url(async_mode=True) == "mysql+aiomysql://u:p@localhost:3306/mydb"


def test_custom_dialect_registration():
    """DialectRegistry를 통한 신규 다이얼렉트 확장 검증"""
    DialectRegistry.register(
        name="cockroachdb",
        default_sync_driver="psycopg2",
        default_async_driver="asyncpg",
        default_port=26257,
        url_scheme_base="cockroachdb"
    )

    info = DialectRegistry.get("cockroachdb")
    assert info.default_port == 26257

    settings = DatabaseSettings(db_type="cockroachdb", database="cockroach_db")
    assert settings.port == 26257
    assert settings.build_url(async_mode=True).startswith("cockroachdb+asyncpg://")
