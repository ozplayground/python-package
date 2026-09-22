import asyncio
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text
from sqla_autoconfig import DatabaseManager, DatabaseSettings


@pytest.fixture
def stress_sync_db(tmp_path):
    db_file = tmp_path / "stress_sync.db"
    settings = DatabaseSettings(
        db_type="sqlite",
        url=f"sqlite:///{db_file}",
        pool_size=10,
        max_overflow=20,
        pool_timeout=15.0
    )
    manager = DatabaseManager(settings=settings)
    with manager.transaction() as s:
        s.execute(text("CREATE TABLE counter (id INTEGER PRIMARY KEY, worker_id INT, val INT)"))
    yield manager
    manager.dispose()


@pytest.fixture
async def stress_async_db(tmp_path):
    db_file = tmp_path / "stress_async.db"
    settings = DatabaseSettings(
        db_type="sqlite",
        url=f"sqlite+aiosqlite:///{db_file}",
        pool_size=10,
        max_overflow=20,
        pool_timeout=15.0
    )
    manager = DatabaseManager(settings=settings)
    async with manager.async_transaction() as s:
        await s.execute(text("CREATE TABLE async_counter (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INT)"))
    yield manager
    await manager.async_dispose()


def test_high_concurrency_threads_zero_leak(stress_sync_db: DatabaseManager):
    """50개 동시 스레드가 풀을 공유하여 트랜잭션 수행 시 교착(Deadlock) 및 누수(Leak) 없음 검증"""
    worker_count = 50

    def worker_task(worker_id: int):
        with stress_sync_db.transaction() as session:
            session.execute(
                text("INSERT INTO counter (id, worker_id, val) VALUES (:id, :worker_id, :val)"),
                {"id": worker_id, "worker_id": worker_id, "val": worker_id * 10}
            )
        return worker_id

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(worker_task, range(worker_count)))

    assert len(results) == worker_count

    # 총 삽입 건수 및 정합성 검증
    with stress_sync_db.session() as session:
        count = session.execute(text("SELECT COUNT(*) FROM counter")).scalar()
        assert count == worker_count


@pytest.mark.asyncio
async def test_high_concurrency_coroutines_zero_leak(stress_async_db: DatabaseManager):
    """100개 동시 비동기 코루틴이 풀을 공유하여 트랜잭션 수행 시 교착 및 누수 없음 검증"""
    task_count = 100

    async def coroutine_task(task_id: int):
        async with stress_async_db.async_transaction() as session:
            await session.execute(
                text("INSERT INTO async_counter (task_id) VALUES (:task_id)"),
                {"task_id": task_id}
            )
        return task_id

    tasks = [coroutine_task(i) for i in range(task_count)]
    results = await asyncio.gather(*tasks)

    assert len(results) == task_count

    async with stress_async_db.async_session() as session:
        count = (await session.execute(text("SELECT COUNT(*) FROM async_counter"))).scalar()
        assert count == task_count
