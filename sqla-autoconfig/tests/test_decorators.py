import inspect
import pytest
from sqlalchemy import text
from sqla_autoconfig import db, DatabaseManager, DatabaseSettings
from sqla_autoconfig.decorators import transactional, async_transactional


@pytest.fixture
def custom_db(tmp_path):
    db_file = tmp_path / "dec_test.db"
    settings = DatabaseSettings(
        db_type="sqlite",
        url=f"sqlite:///{db_file}",
        pool_size=5,
        max_overflow=2
    )
    manager = DatabaseManager(settings=settings)
    with manager.session() as s:
        s.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
        s.commit()
    yield manager
    manager.dispose()


@pytest.fixture
async def async_custom_db(tmp_path):
    db_file = tmp_path / "async_dec_test.db"
    settings = DatabaseSettings(
        db_type="sqlite",
        url=f"sqlite+aiosqlite:///{db_file}",
        pool_size=5,
        max_overflow=2
    )
    manager = DatabaseManager(settings=settings)
    async with manager.async_session() as s:
        await s.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
        await s.commit()
    yield manager
    await manager.async_dispose()


def test_sync_transactional_decorator_with_session_param(custom_db: DatabaseManager):
    """함수에 session 파라미터가 있을 때 자동 주입 및 커밋 검증"""
    @transactional(manager=custom_db)
    def create_user(name: str, session=None):
        session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
        return f"Created {name}"

    result = create_user("Alice")
    assert result == "Created Alice"

    with custom_db.session() as s:
        row = s.execute(text("SELECT name FROM users WHERE name = 'Alice'")).scalar_one_or_none()
        assert row == "Alice"


def test_sync_transactional_decorator_rollback(custom_db: DatabaseManager):
    """함수 내 예외 발생 시 롤백 검증"""
    @transactional(manager=custom_db)
    def fail_user(name: str, session=None):
        session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
        raise RuntimeError("Decorated Failure")

    with pytest.raises(RuntimeError, match="Decorated Failure"):
        fail_user("Bob")

    with custom_db.session() as s:
        row = s.execute(text("SELECT name FROM users WHERE name = 'Bob'")).scalar_one_or_none()
        assert row is None


@pytest.mark.asyncio
async def test_async_transactional_decorator(async_custom_db: DatabaseManager):
    """비동기 함수 데코레이터 주입 및 커밋 검증"""
    @async_transactional(manager=async_custom_db)
    async def create_user_async(name: str, session=None):
        await session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
        return f"Created async {name}"

    res = await create_user_async("Charlie")
    assert res == "Created async Charlie"

    async with async_custom_db.async_session() as s:
        val = (await s.execute(text("SELECT name FROM users WHERE name = 'Charlie'"))).scalar_one()
        assert val == "Charlie"


@pytest.mark.asyncio
async def test_async_transactional_decorator_rollback(async_custom_db: DatabaseManager):
    """비동기 함수 데코레이터 롤백 검증"""
    @async_transactional(manager=async_custom_db)
    async def fail_user_async(name: str, session=None):
        await session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
        raise ValueError("Async Decorator Error")

    with pytest.raises(ValueError, match="Async Decorator Error"):
        await fail_user_async("David")

    async with async_custom_db.async_session() as s:
        val = (await s.execute(text("SELECT name FROM users WHERE name = 'David'"))).scalar_one_or_none()
        assert val is None
