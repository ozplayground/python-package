import json
import os
from pathlib import Path
import pytest
from sqla_autoconfig.config import ConfigLoader, DatabaseSettings
from sqla_autoconfig.exceptions import ConfigurationError, UnsupportedDialectError


def test_default_settings():
    """기본값 로드 검증"""
    settings = DatabaseSettings(db_type="postgres", database="testdb")
    assert settings.db_type == "postgres"
    assert settings.host == "localhost"
    assert settings.port == 5432
    assert settings.user == "postgres"
    assert settings.pool_size == 20
    assert settings.max_overflow == 10
    assert settings.pool_recycle == 1800
    assert settings.pool_pre_ping is True
    assert settings.pool_timeout == 30.0
    assert settings.echo is False


def test_url_special_characters_escaping():
    """비밀번호에 특수문자(@, :, #, /)가 포함된 경우 안전한 URL 인코딩 검증"""
    settings = DatabaseSettings(
        db_type="postgres",
        user="my_user",
        password="p@ss:w/ord#123",
        host="localhost",
        port=5432,
        database="mydb"
    )
    sync_url = settings.build_url(async_mode=False)
    assert "p%40ss%3Aw%2Ford%23123" in sync_url
    assert "@localhost:5432/mydb" in sync_url


def test_unsupported_dialect_validation():
    """지원하지 않는 다이얼렉트 설정 시 예외 발생 검증"""
    with pytest.raises(UnsupportedDialectError):
        DatabaseSettings(db_type="invalid_db", database="testdb")


def test_port_validation():
    """포트 번호 유효 범위(1~65535) 검증"""
    with pytest.raises(ConfigurationError):
        DatabaseSettings(db_type="postgres", port=999999, database="testdb")


def test_cascading_priority_order(tmp_path: Path, monkeypatch):
    """우선순위 검증: 명시적 kwargs > ENV > YAML > JSON > Defaults"""
    json_file = tmp_path / "database.json"
    yaml_file = tmp_path / "database.yaml"

    # 1. JSON 파일 작성 (낮은 우선순위)
    json_data = {
        "db_type": "mysql",
        "database": "json_db",
        "user": "json_user",
        "port": 3306,
        "pool_size": 15
    }
    json_file.write_text(json.dumps(json_data))

    # 2. YAML 파일 작성 (JSON보다 높은 우선순위)
    yaml_data = """
db_type: mariadb
database: yaml_db
user: yaml_user
pool_size: 25
"""
    yaml_file.write_text(yaml_data)

    loader = ConfigLoader(search_paths=[str(tmp_path)])

    # JSON만 있는 경우
    settings_json_only = ConfigLoader(search_paths=[str(tmp_path)]).load_cascading(
        filenames_override={"json": [str(json_file)]}
    )
    assert settings_json_only.database == "json_db"
    assert settings_json_only.pool_size == 15

    # YAML이 함께 있는 경우 -> YAML이 JSON을 덮어씀
    settings_yaml = loader.load_cascading(
        filenames_override={
            "json": [str(json_file)],
            "yaml": [str(yaml_file)]
        }
    )
    assert settings_yaml.db_type == "mariadb"
    assert settings_yaml.database == "yaml_db"
    assert settings_yaml.user == "yaml_user"
    assert settings_yaml.pool_size == 25

    # 3. 환경변수 설정 -> YAML과 JSON을 덮어씀
    monkeypatch.setenv("DB_USER", "env_user")
    monkeypatch.setenv("DB_POOL_SIZE", "50")

    settings_env = loader.load_cascading(
        filenames_override={
            "json": [str(json_file)],
            "yaml": [str(yaml_file)]
        }
    )
    assert settings_env.user == "env_user"
    assert settings_env.pool_size == 50
    # 환경변수로 덮어쓰지 않은 값은 YAML 값 유지
    assert settings_env.database == "yaml_db"

    # 4. 명시적 인자 (kwargs) -> 환경변수까지 덮어씀
    settings_kwargs = loader.load_cascading(
        filenames_override={
            "json": [str(json_file)],
            "yaml": [str(yaml_file)]
        },
        user="explicit_user",
        pool_size=100
    )
    assert settings_kwargs.user == "explicit_user"
    assert settings_kwargs.pool_size == 100


def test_hierarchical_yaml_loading(tmp_path: Path):
    """계층형 YAML 설정 (database.connection / database.pool) 파싱 검증"""
    yaml_file = tmp_path / "hierarchical.yaml"
    yaml_content = """
database:
  type: postgres
  connection:
    host: pg-server
    port: 5433
    user: dbadmin
    password: mypassword
    name: prod_db
  pool:
    size: 30
    max_overflow: 12
    recycle: 1200
    pre_ping: true
    timeout: 40.0
  echo: true
"""
    yaml_file.write_text(yaml_content)

    loader = ConfigLoader(search_paths=[str(tmp_path)])
    settings = loader.load_cascading(
        filenames_override={"yaml": [str(yaml_file)], "json": []}
    )

    assert settings.db_type == "postgres"
    assert settings.host == "pg-server"
    assert settings.port == 5433
    assert settings.user == "dbadmin"
    assert settings.password == "mypassword"
    assert settings.database == "prod_db"
    assert settings.pool_size == 30
    assert settings.max_overflow == 12
    assert settings.pool_recycle == 1200
    assert settings.pool_pre_ping is True
    assert settings.pool_timeout == 40.0
    assert settings.echo is True


def test_hierarchical_json_loading(tmp_path: Path):
    """계층형 JSON 설정 (database.connection / database.pool) 파싱 검증"""
    json_file = tmp_path / "hierarchical.json"
    json_data = {
        "database": {
            "type": "mysql",
            "connection": {
                "host": "mysql-server",
                "port": 3307,
                "user": "root",
                "password": "pwd",
                "name": "app_db"
            },
            "pool": {
                "size": 18,
                "max_overflow": 8,
                "recycle": 900,
                "pre_ping": True,
                "timeout": 20.0
            },
            "echo": False
        }
    }
    json_file.write_text(json.dumps(json_data))

    loader = ConfigLoader(search_paths=[str(tmp_path)])
    settings = loader.load_cascading(
        filenames_override={"json": [str(json_file)], "yaml": []}
    )

    assert settings.db_type == "mysql"
    assert settings.host == "mysql-server"
    assert settings.port == 3307
    assert settings.user == "root"
    assert settings.password == "pwd"
    assert settings.database == "app_db"
    assert settings.pool_size == 18
    assert settings.max_overflow == 8
    assert settings.pool_recycle == 900
    assert settings.pool_pre_ping is True
    assert settings.pool_timeout == 20.0
    assert settings.echo is False

