import pytest
from sqlalchemy import text, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqla_autoconfig.dialects import DialectRegistry
from sqla_autoconfig.manager import DatabaseManager
from sqla_autoconfig.config import DatabaseSettings

# Register sqlite for local in-memory testing
if not DialectRegistry.is_supported("sqlite"):
    DialectRegistry.register(
        name="sqlite",
        default_sync_driver="pysqlite",
        default_async_driver="aiosqlite",
        default_port=0,
        url_scheme_base="sqlite"
    )


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "sync_test.db"
    settings = DatabaseSettings(
        db_type="sqlite",
        url=f"sqlite:///{db_file}",
        pool_size=5,
        max_overflow=2
    )
    manager = DatabaseManager(settings=settings)
    with manager.session() as s:
        Base.metadata.create_all(manager.get_sync_engine())
    yield manager
    manager.dispose()


@pytest.fixture
async def async_db(tmp_path):
    db_file = tmp_path / "async_test.db"
    settings = DatabaseSettings(
        db_type="sqlite",
        url=f"sqlite+aiosqlite:///{db_file}",
        pool_size=5,
        max_overflow=2
    )
    manager = DatabaseManager(settings=settings)
    async with manager.get_async_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield manager
    await manager.async_dispose()


def test_sync_transaction_commit(sync_db: DatabaseManager):
    """동기 트랜잭션 정상 커밋 검증"""
    with sync_db.transaction() as session:
        session.add(Item(name="Apple"))
        # 자동 커밋 기대

    with sync_db.session() as session:
        items = session.query(Item).all()
        assert len(items) == 1
        assert items[0].name == "Apple"


def test_sync_transaction_rollback_on_error(sync_db: DatabaseManager):
    """동기 트랜잭션 예외 발생 시 자동 롤백 검증"""
    with pytest.raises(ValueError, match="Boom"):
        with sync_db.transaction() as session:
            session.add(Item(name="Banana"))
            raise ValueError("Boom")

    with sync_db.session() as session:
        items = session.query(Item).filter_by(name="Banana").all()
        assert len(items) == 0


@pytest.mark.asyncio
async def test_async_transaction_commit(async_db: DatabaseManager):
    """비동기 트랜잭션 정상 커밋 검증"""
    async with async_db.async_transaction() as session:
        session.add(Item(name="Grape"))
        # 자동 커밋 기대

    async with async_db.async_session() as session:
        result = await session.execute(text("SELECT name FROM items WHERE name = 'Grape'"))
        row = result.scalar_one_or_none()
        assert row == "Grape"


@pytest.mark.asyncio
async def test_async_transaction_rollback_on_error(async_db: DatabaseManager):
    """비동기 트랜잭션 예외 발생 시 자동 롤백 검증"""
    with pytest.raises(RuntimeError, match="Async Fail"):
        async with async_db.async_transaction() as session:
            session.add(Item(name="Orange"))
            raise RuntimeError("Async Fail")

    async with async_db.async_session() as session:
        result = await session.execute(text("SELECT name FROM items WHERE name = 'Orange'"))
        row = result.scalar_one_or_none()
        assert row is None


def test_fastapi_dependency_sync(sync_db: DatabaseManager):
    """FastAPI get_db 제너레이터 의존성 검증"""
    gen = sync_db.get_db()
    session = next(gen)
    assert session is not None
    session.add(Item(name="Cherry"))
    session.commit()
    with pytest.raises(StopIteration):
        next(gen)

    with sync_db.session() as s:
        assert s.query(Item).filter_by(name="Cherry").first() is not None


@pytest.mark.asyncio
async def test_fastapi_dependency_async(async_db: DatabaseManager):
    """FastAPI get_async_db 비동기 제너레이터 의존성 검증"""
    gen = async_db.get_async_db()
    session = await anext(gen)
    assert session is not None
    session.add(Item(name="Mango"))
    await session.commit()
    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    async with async_db.async_session() as s:
        res = await s.execute(text("SELECT name FROM items WHERE name = 'Mango'"))
        assert res.scalar_one() == "Mango"
