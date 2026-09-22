import os
import pytest
from sqlalchemy import text
from sqla_autoconfig import db, get_db, get_async_db


def test_global_db_singleton_auto_init(tmp_path, monkeypatch):
    """환경변수 기반 전역 db 싱글톤의 무설정 자동 초기화 검증"""
    db_file = tmp_path / "global_auto.db"
    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    # 전역 db 인스턴스 초기화 리셋
    db._instance = None

    with db.session() as s:
        s.execute(text("CREATE TABLE test_auto (id INT, val TEXT)"))
        s.execute(text("INSERT INTO test_auto VALUES (1, 'hello')"))
        s.commit()

    with db.session() as s:
        val = s.execute(text("SELECT val FROM test_auto WHERE id = 1")).scalar_one()
        assert val == "hello"
