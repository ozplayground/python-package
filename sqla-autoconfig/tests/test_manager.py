import pytest
from sqlalchemy.pool import QueuePool
from sqla_autoconfig.manager import DatabaseManager
from sqla_autoconfig.config import DatabaseSettings


def test_manager_engine_pool_parameters():
    """PostgreSQL 설정 시 Engine에 QueuePool 및 지정된 파라미터가 정확히 주입되는지 검증"""
    settings = DatabaseSettings(
        db_type="postgres",
        host="localhost",
        port=5432,
        user="testuser",
        password="secret",
        database="proddb",
        pool_size=35,
        max_overflow=15,
        pool_recycle=900,
        pool_pre_ping=True,
        pool_timeout=45.0,
        echo=True
    )
    manager = DatabaseManager(settings=settings)

    # 엔진 객체 생성 (실제 연결 시도 없이 엔진 생성 파라미터 확인)
    engine = manager.get_sync_engine()
    assert engine.url.database == "proddb"
    assert engine.url.username == "testuser"
    assert engine.echo is True

    # 커넥션 풀 파라미터 검증
    pool = engine.pool
    assert isinstance(pool, QueuePool)
    assert pool.size() == 35
    assert pool._max_overflow == 15
    assert pool._recycle == 900
    assert pool._pre_ping is True
    assert pool._timeout == 45.0

    manager.dispose()
    assert manager._sync_engine is None


def test_manager_lazy_initialization():
    """DatabaseManager 생성 시 엔진이 즉시 초기화되지 않고 지연 로드(lazy init)되는지 검증"""
    settings = DatabaseSettings(db_type="postgres", database="lazydb")
    manager = DatabaseManager(settings=settings)
    assert manager._sync_engine is None
    assert manager._async_engine is None

    # 요청 시 초기화
    _ = manager.get_sync_engine()
    assert manager._sync_engine is not None
    manager.dispose()
