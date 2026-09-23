# sqla-autoconfig

> **Database Auto-Configuration & Connection Pool Manager for Python (SQLAlchemy 2.0)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy 2.0+](https://img.shields.io/badge/sqlalchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`sqla-autoconfig`는 환경변수(`DB_*` / `SQLA_*`) 또는 설정 파일(`database.yaml`, `database.json`)을 기반으로 커넥션 풀과 세션/트랜잭션 라이프사이클을 자동 구성하는 SQLAlchemy 2.0 라이브러리입니다.

매 마이크로서비스마다 반복되는 `create_engine`, `sessionmaker`, 컨텍스트 매니저, 그리고 방화벽 유휴 단절(Idle Disconnect) 대응 코드를 표준화하여 커넥션 누수와 설정 오류를 방지합니다.

---

## 🛠️ 핵심 기능

- **자동 구성 인스턴스 (`from sqla_autoconfig import db`)**:
  - 별도의 설정 코드 없이 환경변수나 설정 파일을 감지하여 엔진과 세션 팩토리를 지연 로딩(Lazy Loading) 방식으로 초기화합니다.
- **5단계 계층형 설정 탐색 (Cascading Config Discovery)**:
  - `명시적 인자 (kwargs)` > `환경변수 (DB_* / SQLA_*)` > `YAML (database.yaml)` > `JSON (database.json)` > `기본값` 순서로 병합합니다.
  - 비밀번호에 포함된 특수문자(`@`, `:`, `/` 등)는 내부적으로 자동 인코딩 처리되어 DSN 구문 오류를 방지합니다.
- **프로덕션 커넥션 풀 튜닝 (QueuePool)**:
  - `pool_pre_ping=True`: 세션 체크아웃 시 소켓 유효성을 사전 검증하여 AWS RDS 다중 AZ Failover 등으로 끊어진 연결을 자동 감지하고 복구합니다.
  - `pool_recycle=1800`: 30분 주기로 유휴 커넥션을 재생성하여 중간 방화벽(L4/NAT)의 TCP 강제 단절을 사전에 예방합니다.
  - 기본값(`pool_size=20`, `max_overflow=10`, `pool_timeout=30.0s`)을 통해 일반적인 트래픽 버스트에 대응합니다.
- **동기 및 비동기(AsyncIO) 지원**:
  - 동기: `with db.transaction() as session`, `@db.transactional`, `Depends(db.get_db)`
  - 비동기: `async with db.async_transaction() as session`, `@db.async_transactional`, `Depends(db.get_async_db)`
- **다중 RDBMS 및 다이얼렉트 확장 (`DialectRegistry`)**:
  - PostgreSQL (`psycopg2` / `asyncpg`)
  - MySQL / MariaDB (`pymysql` / `aiomysql`)
  - SQLite (인메모리 및 파일)
  - `DialectRegistry.register(...)`를 통해 Oracle, MSSQL, CockroachDB 등 커스텀 다이얼렉트를 손쉽게 등록할 수 있습니다.

---

## 📦 설치

```bash
# 기본 설치 (SQLite 기본 포함)
pip install sqla-autoconfig

# RDBMS별 드라이버 포함 설치
pip install "sqla-autoconfig[postgres]"    # psycopg2 + asyncpg
pip install "sqla-autoconfig[mysql]"       # pymysql + aiomysql
pip install "sqla-autoconfig[all]"         # 전체 드라이버
```

---

## ⚙️ 설정 가이드

설정은 환경변수(`DB_*` 또는 `SQLA_*`), `database.yaml`, `database.json` 파일을 통해 유연하게 관리할 수 있습니다.

### 1) 환경변수 설정 (`.env` 또는 컨테이너 환경)
```bash
# 기본 데이터베이스 접속 정보
export DB_TYPE=postgres            # postgres, mysql, mariadb, sqlite
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=myuser
export DB_PASSWORD=my_secret_password
export DB_NAME=my_service_db

# 커넥션 풀 파라미터 (미지정 시 운영 권장 기본값 적용)
export DB_POOL_SIZE=20             # 기본 상주 커넥션 수
export DB_MAX_OVERFLOW=10          # 버스트 시 추가 허용 커넥션 수
export DB_POOL_RECYCLE=1800        # 30분 주기 커넥션 재생성
export DB_POOL_PRE_PING=true       # 좀비 커넥션 자동 감지 및 제거
export DB_POOL_TIMEOUT=30.0        # 커넥션 획득 대기 타임아웃 (초)
export DB_ECHO=false               # SQL 쿼리 로깅 (운영은 false 권장)

# 또는 전체 DSN URL로 직접 지정 (지정 시 host/user/password 설정은 무시됨)
# export DATABASE_URL=postgresql+asyncpg://myuser:my_password@localhost:5432/my_service_db
```

### 2) YAML 설정 파일 (`database.yaml`)
계층형 구조와 플랫(Flat) 구조를 모두 지원합니다:

```yaml
# database.yaml: 프로젝트 루트 또는 config/ 디렉토리에 위치
database:
  type: postgres
  connection:
    host: localhost
    port: 5432
    user: myuser
    password: "my_secret_password#123"
    name: my_service_db
  pool:
    size: 20
    max_overflow: 10
    recycle: 1800
    pre_ping: true
    timeout: 30.0
  echo: false
```

### 3) 지원 파라미터 매핑표
| 파라미터 (YAML/JSON) | 환경변수 매핑 | 타입 | 기본값 | 설명 |
| :--- | :--- | :---: | :---: | :--- |
| `db_type` | `DB_TYPE` / `SQLA_DB_TYPE` | string | `postgres` | 데이터베이스 종류 (`postgres`, `mysql`, `mariadb`, `sqlite`) |
| `host` | `DB_HOST` / `SQLA_HOST` | string | `localhost` | 호스트 도메인 또는 IP |
| `port` | `DB_PORT` / `SQLA_PORT` | int | DB별 기본 | 포트 번호 (PostgreSQL: 5432, MySQL: 3306) |
| `user` | `DB_USER` / `SQLA_USER` | string | DB별 기본 | 접속 계정 (PostgreSQL: `postgres`, MySQL: `root`) |
| `password` | `DB_PASSWORD` / `SQLA_PASSWORD` | string | `""` | 계정 비밀번호 (특수문자 자동 URL 인코딩 처리) |
| `database` | `DB_NAME` / `SQLA_DATABASE` | string | `test` | 접속할 데이터베이스 이름 |
| `url` | `DATABASE_URL` / `SQLA_DATABASE_URL`| string | `None` | SQLAlchemy 전체 접속 DSN (설정 시 개별 접속 정보 대체) |
| `pool_size` | `DB_POOL_SIZE` | int | `20` | 기본 커넥션 풀 크기 |
| `max_overflow` | `DB_MAX_OVERFLOW` | int | `10` | 풀 초과 시 생성 가능한 최대 추가 커넥션 수 |
| `pool_recycle` | `DB_POOL_RECYCLE` | int | `1800` | 커넥션 유휴 시간 경과 시 재생성 주기 (초 단위) |
| `pool_pre_ping` | `DB_POOL_PRE_PING` | bool | `true` | 체크아웃 전 유효성 검사 활성화 여부 |
| `pool_timeout` | `DB_POOL_TIMEOUT` | float | `30.0` | 풀 고갈 시 대기 타임아웃 (초 단위) |
| `echo` | `DB_ECHO` / `SQLA_ECHO` | bool | `false` | SQL 로깅 출력 여부 |

---

## 🚀 실무 사용 예제

### 1. 트랜잭션 컨텍스트 매니저 (자동 커밋 & 롤백)
블록 정상 종료 시 `commit()`, 예외 발생 시 `rollback()`, 종료 시 세션을 자동으로 풀에 반환(`close()`)합니다:

```python
from sqla_autoconfig import db
from sqlalchemy import text

# 동기 트랜잭션
with db.transaction() as session:
    session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": "Alice"})

# 비동기 트랜잭션
async def main():
    async with db.async_transaction() as session:
        await session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": "Bob"})
```

### 2. 선언적 트랜잭션 데코레이터 (`@transactional`)
함수 호출 시 `session` 인자가 없으면 활성 트랜잭션 세션을 생성하여 자동 주입합니다:

```python
from sqla_autoconfig import db
from sqlalchemy import text

@db.transactional
def create_user(name: str, session=None):
    session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
    return f"User {name} created"

@db.async_transactional
async def create_user_async(name: str, session=None):
    await session.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": name})
    return f"User {name} created"
```

### 3. FastAPI 연동 및 Lifespan 수명주기 관리
컨테이너 환경에서 롤링 배포나 프로세스 종료 시 커넥션 풀을 안전하게 회수합니다:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqla_autoconfig import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작
    yield
    # 프로세스 종료 시 열린 비동기 커넥션 풀 정리
    await db.async_dispose()

app = FastAPI(lifespan=lifespan)

# 동기 엔드포인트
@app.get("/sync-users")
def get_users(session: Session = Depends(db.get_db)):
    return session.execute(text("SELECT id, name FROM users")).mappings().all()

# 비동기 엔드포인트
@app.get("/async-users")
async def get_users_async(session: AsyncSession = Depends(db.get_async_db)):
    result = await session.execute(text("SELECT id, name FROM users"))
    return result.mappings().all()
```

### 4. 독립 인스턴스 생성 (다중 DB / Read-Write 분리)
기본 `db` 싱글톤 외에 별도의 데이터베이스나 분석용 읽기 전용 DB가 필요한 경우:

```python
from sqla_autoconfig import DatabaseManager

analytics_db = DatabaseManager(
    db_type="postgres",
    host="analytics-db.internal",
    database="analytics",
    pool_size=10,
    max_overflow=5
)

with analytics_db.transaction() as session:
    ...
```

---

## 💡 운영 모범 사례 (Production Gotchas)

1. **커넥션 풀 고갈(`QueuePool limit reached`) 방어**:
   - `with db.transaction():` 블록 내부에 외부 API 호출(HTTP, gRPC, 메시지 큐 등)을 포함하지 마세요. 외부 호출이 지연되면 커넥션을 장시간 점유하여 풀이 고갈됩니다.
   - 전체 파드(Pod) 수가 늘어날 경우 파드당 `pool_size + max_overflow` 합계가 DB 서버의 `max_connections` 한도를 넘지 않도록 계산하여 설정하세요.
2. **비밀번호 특수문자 안전 처리**:
   - 비밀번호에 특수문자가 포함되어 있어도 `sqla-autoconfig`가 자동으로 URL 인코딩(`quote_plus`)을 처리하므로 DSN 에러 걱정 없이 원본 값을 환경변수에 주입할 수 있습니다.
3. **비동기 런타임 종료 훅**:
   - `atexit` 훅은 동기 엔진을 자동으로 정리하지만, 비동기 `AsyncEngine`은 이벤트 루프가 닫히기 전에 `await db.async_dispose()`를 호출해야 깔끔하게 종료됩니다. FastAPI의 `lifespan` 컨텍스트 매니저를 사용하는 것을 권장합니다.

---

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest --cov=sqla_autoconfig tests/

# 동시성 부하 테스트
pytest tests/test_concurrency.py
```

---

## 📄 라이선스

MIT License.
