# sqla-autoconfig

> **Database Auto-Configuration & High-Concurrency Connection Pool Manager for Python (SQLAlchemy 2.0)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy 2.0+](https://img.shields.io/badge/sqlalchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`sqla-autoconfig`는 설정 파일(`database.yaml`, `database.json`)이나 환경변수만으로 **최적화된 커넥션 풀과 세션/트랜잭션 컨텍스트 매니저를 즉시 제공하는 파이썬 데이터베이스 자동 구성 라이브러리**입니다.

매 프로젝트마다 반복되던 30~50줄의 SQLAlchemy `create_engine`, `sessionmaker`, `contextmanager` 보일러플레이트를 **단 1줄**로 줄여줍니다.

---

## ✨ 핵심 기능 (Key Features)

- **Zero-Boilerplate Auto-Configuration**: `from sqla_autoconfig import db`만으로 즉시 사용 가능.
- **계층형 설정 탐색 (Cascading Config Discovery)**:
  `명시적 인자 (kwargs)` > `환경변수 (ENV)` > `YAML` > `JSON` > `기본값 (Defaults)` 4단계 우선순위 자동 병합.
- **대규모 동접(High-Concurrency) 대응 무장애 커넥션 풀**:
  - `QueuePool` 및 `AsyncAdaptedQueuePool` 기반
  - `pool_pre_ping=True` (좀비 커넥션 자동 퇴출 및 복구)
  - `pool_size=20`, `max_overflow=10`, `pool_recycle=1800` 최적 기본값 적용
  - 교착(Deadlock) 및 커넥션 누수(Zero-Leak) 원천 차단
- **동기 & 비동기 완벽 지원**:
  - 동기: `with db.session()`, `with db.transaction()`, `@db.transactional`
  - 비동기: `async with db.async_session()`, `async with db.async_transaction()`, `@db.async_transactional`
- **다중 RDBMS 지원 & 무한 확장성 (DialectRegistry)**:
  - PostgreSQL (`psycopg2` / `asyncpg`)
  - MySQL (`pymysql` / `aiomysql`)
  - MariaDB (`pymysql` / `aiomysql`)
  - SQLite (내장 지원)
  - `DialectRegistry.register(...)`로 Oracle, MSSQL, CockroachDB 등 손쉬운 확장
- **FastAPI 네이티브 연동**: `Depends(db.get_db)`, `Depends(db.get_async_db)` 지원.

---

## 📦 설치 (Installation)

```bash
# 기본 설치 (SQLAlchemy + Pydantic + PyYAML)
pip install sqla-autoconfig

# 특정 RDBMS 드라이버 포함 설치
pip install "sqla-autoconfig[postgres]"    # psycopg2 + asyncpg
pip install "sqla-autoconfig[mysql]"       # pymysql + aiomysql
pip install "sqla-autoconfig[all]"         # 모든 드라이버
```

---

## ⚙️ 설정 우선순위 (Configuration Precedence)

설정값은 다음 우선순위로 자동 병합됩니다:
1. **명시적 인자 (`kwargs`)**
2. **환경변수 (`DB_*` or `SQLA_*`)**
3. **YAML 파일 (`database.yaml`, `database.yml`, `config.yaml`, `application.yml`)**
4. **JSON 파일 (`database.json`, `config.json`, `application.json`)**
5. **기본값 (Defaults)**

### 1) 환경변수 예시 (`.env` 또는 Shell)
```bash
# 기본 데이터베이스 접속 정보
export DB_TYPE=postgres            # postgres, mysql, mariadb, sqlite
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=myuser
export DB_PASSWORD=my_secret_password
export DB_NAME=my_service_db

# 대규모 동시접속 풀 튜닝 (기본값이 이미 프로덕션 최적화 상태)
export DB_POOL_SIZE=20             # 상시 유지 커넥션 수
export DB_MAX_OVERFLOW=10          # 버스트 시 추가 허용 커넥션 수
export DB_POOL_RECYCLE=1800        # 30분 주기 커넥션 재생성 (유휴 단절 방지)
export DB_POOL_PRE_PING=true       # 체크아웃 시 좀비 커넥션 자동 퇴출
export DB_POOL_TIMEOUT=30.0        # 커넥션 획득 대기 타임아웃 (초)
export DB_ECHO=false               # 쿼리 로깅 활성화 여부

# 또는 단일 Connection URL로 직접 지정 (지정 시 host/port 등 무시)
# export DATABASE_URL=postgresql+asyncpg://myuser:my_secret_password@localhost:5432/my_service_db
```

### 2) YAML 파일 예시 (`database.yaml` 또는 `database.yml`)
```yaml
# database.yaml (계층형 구조 지원)
database:
  type: postgres
  connection:
    host: localhost
    port: 5432
    user: myuser
    password: my_secret_password
    name: my_service_db
  pool:
    size: 20
    max_overflow: 10
    recycle: 1800
    pre_ping: true
    timeout: 30.0
  echo: false
```

### 3) JSON 파일 예시 (`database.json` 또는 `config.json`)
```json
{
  "database": {
    "type": "mysql",
    "connection": {
      "host": "127.0.0.1",
      "port": 3306,
      "user": "root",
      "password": "root_password",
      "name": "my_service_db"
    },
    "pool": {
      "size": 25,
      "max_overflow": 15,
      "recycle": 1800,
      "pre_ping": true,
      "timeout": 30.0
    },
    "echo": false
  }
}
```

### 4) 지원 파라미터 상세
| 설정 키 (YAML/JSON) | 환경변수 매핑 | 타입 | 기본값 | 설명 |
| :--- | :--- | :---: | :---: | :--- |
| `db_type` | `DB_TYPE` | string | `postgres` | 데이터베이스 종류 (`postgres`, `mysql`, `mariadb`, `sqlite`) |
| `host` | `DB_HOST` | string | `localhost` | 데이터베이스 호스트 주소 |
| `port` | `DB_PORT` | int | DB별 기본 | 포트 번호 (PostgreSQL: 5432, MySQL/MariaDB: 3306) |
| `user` | `DB_USER` | string | DB별 기본 | 사용자 계정 (PostgreSQL: `postgres`, MySQL: `root`) |
| `password` | `DB_PASSWORD` | string | `""` | 접속 비밀번호 (특수문자 자동 URL 인코딩) |
| `database` | `DB_NAME` | string | `test` | 데이터베이스 이름 |
| `url` | `DATABASE_URL` | string | `None` | SQLAlchemy 전체 연결 URL (지정 시 개별 접속 정보 무시) |
| `pool_size` | `DB_POOL_SIZE` | int | `20` | 기본 커넥션 풀 크기 |
| `max_overflow` | `DB_MAX_OVERFLOW` | int | `10` | 풀 초과 시 생성 가능한 최대 추가 커넥션 수 |
| `pool_recycle` | `DB_POOL_RECYCLE` | int | `1800` | 커넥션 유휴 시간 경과 시 재생성 주기 (초) |
| `pool_pre_ping` | `DB_POOL_PRE_PING` | bool | `true` | 커넥션 체크아웃 전 유효성 사전 검증 (좀비 커넥션 방지) |
| `pool_timeout` | `DB_POOL_TIMEOUT` | float | `30.0` | 커넥션 고갈 시 대기 타임아웃 (초) |
| `echo` | `DB_ECHO` | bool | `false` | 실행되는 SQL 문 콘솔 출력 여부 |

---

## 🚀 사용법 (Usage)

### 1. 트랜잭션 컨텍스트 매니저 (자동 커밋 & 롤백)
```python
from sqla_autoconfig import db
from sqlalchemy import text

# 동기 트랜잭션 (정상 완료 시 commit, 예외 발생 시 rollback, 종료 시 close)
with db.transaction() as session:
    session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": "Alice"})

# 비동기 트랜잭션
async def main():
    async with db.async_transaction() as session:
        await session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": "Bob"})
```

### 2. 선언적 트랜잭션 데코레이터 (`@transactional`)
```python
from sqla_autoconfig import db
from sqlalchemy import text

# session 매개변수가 있으면 활성 트랜잭션 세션이 자동 주입됩니다.
@db.transactional
def create_user(name: str, session=None):
    session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
    return f"User {name} created"

# 비동기 코루틴 데코레이터
@db.async_transactional
async def create_user_async(name: str, session=None):
    await session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
    return f"User {name} created"
```

### 3. FastAPI 의존성 주입 연동
```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqla_autoconfig import db

app = FastAPI()

# 동기 엔드포인트
@app.get("/sync-users")
def get_users(session: Session = Depends(db.get_db)):
    return session.execute(text("SELECT * FROM users")).fetchall()

# 비동기 엔드포인트
@app.get("/async-users")
async def get_users_async(session: AsyncSession = Depends(db.get_async_db)):
    result = await session.execute(text("SELECT * FROM users"))
    return result.fetchall()
```

### 4. 독립 인스턴스 생성 (다중 DB / Read-Write 분리)
```python
from sqla_autoconfig import DatabaseManager, DatabaseSettings

# 특정 설정을 가진 독립 매니저 생성
analytics_db = DatabaseManager(
    db_type="postgres",
    host="analytics-host",
    database="analytics",
    pool_size=10
)

with analytics_db.transaction() as session:
    ...
```

### 5. 신규 RDBMS 다이얼렉트 확장
```python
from sqla_autoconfig import DialectRegistry

# 새 다이얼렉트 등록
DialectRegistry.register(
    name="cockroachdb",
    default_sync_driver="psycopg2",
    default_async_driver="asyncpg",
    default_port=26257,
    url_scheme_base="cockroachdb"
)
```

---

## 🧪 테스트 (Testing)

```bash
# 전체 테스트 실행 (커버리지 포함)
pytest --cov=sqla_autoconfig tests/

# 동시성 스트레스 테스트 실행
pytest tests/test_concurrency.py
```

---

## 📄 라이선스 (License)

MIT License.
