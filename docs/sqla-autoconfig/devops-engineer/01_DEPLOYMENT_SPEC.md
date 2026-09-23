# [sqla-autoconfig] 패키지 배포 및 환경 검증 명세서 (Deployment Specification)

- **작성일자**: 2026-09-22
- **작성자**: 데브옵스 엔지니어 (`devops-engineer`)
- **문서 버전**: v1.1
- **상태**: Approved

---

## 1. 패키지 빌드 및 배포 산출물 (Package Artifacts)

### 1.1 빌드 산출물 명세
`sqla-autoconfig` 패키지는 Python 3.10 이상을 지원하며, PEP 517/621 표준과 `hatchling` 빌드 백엔드를 기반으로 순수 파이썬 휠(Pure Python Wheel)과 소스 배포판(sdist)을 생성합니다.

| 패키지 유형 | 파일명 | 형식 | 크기 | 빌드 상태 | 규격 검증 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Source Distribution (sdist)** | `sqla_autoconfig-0.1.0.tar.gz` | tar.gz | 약 20.3KB | **BUILD SUCCESS** | POSIX tar archive (gzip 압축), 소스 및 테스트 스위트 포함 |
| **Pure Python Wheel** | `sqla_autoconfig-0.1.0-py3-none-any.whl` | Wheel | 약 13.8KB | **BUILD SUCCESS** | PEP 427 호환 (`py3-none-any`), C 확장 컴파일 불필요 |

### 1.2 패키지 포함 모듈 무결성 검증
휠 아카이브 내 핵심 모듈 및 파일 목록 검증 결과:
- `sqla_autoconfig/__init__.py`: 패키지 진입점, 기본 `db` 인스턴스 및 공개 심볼 익스포트
- `sqla_autoconfig/config.py`: `DatabaseSettings`, `ConfigLoader` (계층형 우선순위 로더)
- `sqla_autoconfig/manager.py`: `DatabaseManager` (커넥션 풀, 세션 팩토리, `atexit` 훅)
- `sqla_autoconfig/context.py`: 세션/트랜잭션 컨텍스트 매니저 및 FastAPI 의존성 제너레이터
- `sqla_autoconfig/decorators.py`: `@db.transactional`, `@db.async_transactional` 데코레이터
- `sqla_autoconfig/dialects.py`: `DialectRegistry` (다중 RDBMS 드라이버 및 포트 매핑)
- `sqla_autoconfig/exceptions.py`: `SqlaAutoconfigError`, `ConfigurationError`, `UnsupportedDialectError`

### 1.3 `uv` 기반 빌드 및 PyPI 배포 파이프라인
운영 배포 시 재현 가능성과 산출물 무결성을 보장하기 위해 `uv` 도구를 사용합니다.

```bash
# 1. 기존 빌드 산출물 정리 및 빌드 실행
rm -rf dist/
uv build

# 2. 빌드 산출물 아카이브 무결성 검증
ls -lh dist/
tar -ztvf dist/sqla_autoconfig-0.1.0.tar.gz
unzip -l dist/sqla_autoconfig-0.1.0-py3-none-any.whl

# 3. TestPyPI 사전 배포 검증 (Staging 단계)
uv publish --publish-url https://test.pypi.org/legacy/ --token "$TEST_PYPI_API_TOKEN"

# 4. PyPI 공식 배포 (Production 단계)
uv publish --token "$PYPI_API_TOKEN"
```

---

## 2. 계층형 환경변수 및 설정 파일 규격서 (Environment & Config Specification)

### 2.1 설정 우선순위 매트릭스 (Precedence Matrix)
`ConfigLoader`는 다단계 우선순위를 기반으로 데이터베이스 설정을 심층 병합(Deep Merge)합니다.

```mermaid
flowchart TD
    A["1. 명시적 인자 (kwargs)<br/>코드 레벨 오버라이드"] --> B["2. 환경변수 (DB_* 또는 SQLA_*)<br/>K8s ConfigMap/Secret 주입"]
    B --> C["3. YAML 파일<br/>(database.yaml / config.yaml)"]
    C --> D["4. JSON 파일<br/>(database.json / config.json)"]
    D --> E["5. 코드 기본값 (Defaults)<br/>PostgreSQL 기본값 및 QueuePool 최적화"]
```

1. **명시적 전달 인자 (`kwargs`)**: `DatabaseManager(host="db.prod", ...)` 형태로 전달 시 최우선 적용.
2. **환경변수 (`DB_*` 또는 `SQLA_*`)**: 컨테이너 런타임에서 주입되는 설정.
3. **YAML 파일 (`database.yaml`, `database.yml`, `config.yaml`, `application.yml`)**: 계층형/플랫 구조 지원.
4. **JSON 파일 (`database.json`, `config.json`, `application.json`)**: 범용 마이크로서비스 설정 연동.
5. **기본값 (Hardcoded Defaults)**: 외부 설정 부재 시 `db_type="postgres"`, `pool_size=20`, `max_overflow=10`, `pool_recycle=1800` 등 안전한 운영 기본값 주입.

### 2.2 `.env.example`
운영 컨테이너 및 로컬 개발 환경용 환경변수 템플릿입니다:

```ini
# ==============================================================================
# sqla-autoconfig 환경변수 템플릿 (.env.example)
# 접두사: DB_* 또는 SQLA_* 지원 (동일 변수 존재 시 SQLA_*가 우선 적용)
# ==============================================================================

# [기본 접속 정보]
DB_TYPE=postgres            # 지원 다이얼렉트: postgres, mysql, mariadb, sqlite
DB_HOST=localhost
DB_PORT=5432                # 미지정 시 다이얼렉트 기본 포트(postgres: 5432, mysql: 3306) 자동 적용
DB_USER=myuser              # 미지정 시 다이얼렉트 기본 유저(postgres: postgres, mysql: root) 자동 적용
DB_PASSWORD=secret_password # 특수문자(@, :, /, # 등)는 URL 생성 시 자동 인코딩됨
DB_NAME=production_db

# [단일 접속 URL 오버라이드 (선택 사항)]
# DATABASE_URL이 설정되면 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD 설정은 무시됩니다.
# DATABASE_URL=postgresql+asyncpg://myuser:secret@localhost:5432/production_db

# [커넥션 풀 및 신뢰성 튜닝]
DB_POOL_SIZE=20             # 기본 상주 커넥션 수 (QueuePool)
DB_MAX_OVERFLOW=10          # 트래픽 버스트 시 추가 허용 커넥션 수
DB_POOL_RECYCLE=1800        # 유휴 커넥션 재생성 주기 (초 단위, 방화벽 Idle Timeout 방지)
DB_POOL_PRE_PING=true       # 체크아웃 전 유효성 검증 (좀비 커넥션 자동 퇴출)
DB_POOL_TIMEOUT=30.0        # 풀 고갈 시 커넥션 획득 대기 타임아웃 (초 단위)
DB_ECHO=false               # SQL 쿼리 로깅 활성화 여부 (운영 환경에서는 반드시 false 유지)
```

### 2.3 `database.yaml` 예시 (계층형 및 플랫 지원)
`ConfigLoader`는 `database`, `sqla`, `db` 네임스페이스와 내부 `connection`, `pool` 계층 구조를 자동으로 감지하여 정규화합니다.

```yaml
# database.yaml: 계층형 구조 예시
database:
  type: postgres
  connection:
    host: localhost
    port: 5432
    user: app_user
    password: "app_password#123"
    name: app_db
  pool:
    size: 20
    max_overflow: 10
    recycle: 1800
    pre_ping: true
    timeout: 30.0
  echo: false
```

### 2.4 `database.json` 예시
```json
{
  "database": {
    "type": "mysql",
    "connection": {
      "host": "127.0.0.1",
      "port": 3306,
      "user": "root",
      "password": "root_password",
      "name": "app_db"
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

### 2.5 환경변수 및 설정 우선순위 오적용 시 디버깅 방법 (Gotchas)
운영자가 환경변수를 주입했으나 의도한 대로 동작하지 않을 때 점검해야 할 핵심 포인트입니다:

1. **단일 URL(`DATABASE_URL`)의 우선순위 충돌**:
   - `DATABASE_URL` 또는 `SQLA_DATABASE_URL`이 환경변수에 존재하면, 개별 지정된 `DB_HOST`, `DB_PORT`, `DB_USER` 등은 완전히 무시됩니다.
   - 쿠버네티스 배포 매니페스트에서 ConfigMap의 `DB_HOST`와 Secret의 `DATABASE_URL`이 동시에 주입되지 않았는지 확인해야 합니다.
2. **특수문자 포함 비밀번호 인코딩**:
   - 비밀번호에 `@`, `:`, `/`, `#` 등이 포함된 경우 수동으로 연결 문자열을 작성하면 SQLAlchemy DSN 파싱 오류가 발생합니다.
   - `sqla-autoconfig`는 `DatabaseSettings.build_url()` 내부에서 `urllib.parse.quote_plus`를 사용하여 계정명과 비밀번호를 자동으로 인코딩하므로 별도의 수동 인코딩 없이 원본 비밀번호를 전달하면 됩니다.
3. **환경변수 접두사 이중 지원 (`DB_*` vs `SQLA_*`)**:
   - 로더는 `DB_*`와 `SQLA_*` 두 접두사를 모두 매핑합니다. 만약 `DB_HOST=10.0.0.1`과 `SQLA_HOST=10.0.0.2`가 동시에 주입되면 매핑 순서에 따라 `SQLA_*`가 최종 값을 덮어씁니다. 일관된 단일 접두사 사용을 권장합니다.
4. **포트 및 다이얼렉트 유효성 검증 Failsafe**:
   - `db_type`이 지원하지 않는 다이얼렉트이거나, `port`가 1~65535 범위를 벗어날 경우 앱 기동 즉시 `ConfigurationError` 또는 `UnsupportedDialectError`를 발생시켜 잘못된 설정으로 서비스가 시작되는 것을 차단합니다.

---

## 3. 다중 데이터베이스 통합 테스트베드 (Docker Compose Testbed)

PostgreSQL, MySQL, MariaDB와의 라이브 통합 검증을 위한 Docker Compose 명세입니다.

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: test-postgres
    environment:
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpassword
      POSTGRES_DB: testdb
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d testdb"]
      interval: 5s
      timeout: 5s
      retries: 5

  mysql:
    image: mysql:8.0
    container_name: test-mysql
    environment:
      MYSQL_ROOT_PASSWORD: testpassword
      MYSQL_DATABASE: testdb
      MYSQL_USER: testuser
      MYSQL_PASSWORD: testpassword
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "testuser", "-ptestpassword"]
      interval: 5s
      timeout: 5s
      retries: 5

  mariadb:
    image: mariadb:10.11
    container_name: test-mariadb
    environment:
      MARIADB_ROOT_PASSWORD: testpassword
      MARIADB_DATABASE: testdb
      MARIADB_USER: testuser
      MARIADB_PASSWORD: testpassword
    ports:
      - "3307:3306"
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 5s
      timeout: 5s
      retries: 5
```

---

## 4. 프로덕션 운영 및 커넥션 풀 신뢰성 가이드 (Production Reliability Runbook)

### 4.1 커넥션 풀 고갈(`QueuePool limit reached`) 원인 및 튜닝
대규모 동시 요청 유입 시 가장 빈번하게 발생하는 데이터베이스 계층 장애입니다.

#### 장애 증상 및 로그
```text
sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached, connection timed out, timeout 30.00
```
- **원인**: 활성 트랜잭션 수가 `pool_size + max_overflow`(기본 30개)에 도달한 상태에서 신규 세션 요청이 `pool_timeout`(기본 30초) 동안 대기하다 타임아웃으로 실패합니다.
- **운영 튜닝 및 진단 절차**:
  1. **트랜잭션 내부 블로킹 I/O 점검 (코드 레벨)**:
     - `with db.transaction():` 또는 `@db.transactional` 내부에서 외부 HTTP API 호출이나 무거운 연산을 수행하고 있는지 확인합니다. 트랜잭션 컨텍스트는 데이터베이스 I/O만 포함하도록 범위를 좁혀야 합니다.
  2. **파드(Pod)별 풀 크기 및 DB 인스턴스 최대 커넥션 계산**:
     - 공식: `(전체 파드 수) * (pool_size + max_overflow) < (DB 서버 max_connections) * 0.8`
     - 예: RDS `max_connections=500`이고 파드가 10개라면, 파드당 최대 허용 커넥션은 `500 * 0.8 / 10 = 40`개 이하로 설정해야 DB 서버의 `Too many connections` 에러를 방지할 수 있습니다.
  3. **대규모 환경에서의 인프라 풀러 도입**:
     - 파드 수가 수십 개 이상으로 스케일아웃되는 경우 애플리케이션 풀 크기를 무한정 늘리지 말고, PgBouncer(트랜잭션 풀링 모드)나 AWS RDS Proxy를 데이터베이스 앞단에 배치하는 것을 권장합니다.

| 파라미터 | 기본값 | 일반 마이크로서비스 | 대용량 트래픽 서비스 | 튜닝 기준 |
| :--- | :---: | :---: | :---: | :--- |
| `pool_size` | `20` | `10` ~ `20` | `30` ~ `50` | 상시 유지 커넥션 수 (`QueuePool`). DB 인스턴스 메모리 감안. |
| `max_overflow` | `10` | `5` ~ `10` | `15` ~ `25` | 트래픽 버스트 시 임시 추가 생성 커넥션. |
| `pool_recycle` | `1800`s | `1800`s (30분) | `900` ~ `1800`s | 방화벽 Idle Timeout보다 작게 설정하여 유휴 단절 예방. |
| `pool_pre_ping` | `true` | `true` | `true` | 체크아웃 시 소켓 유효성 검사. 좀비 커넥션 제거 필수. |
| `pool_timeout` | `30.0`s | `10.0` ~ `30.0`s | `5.0` ~ `10.0`s | 대기 타임아웃. 과도한 지연 누적 방지를 위해 조정. |

### 4.2 좀비 커넥션 및 유휴 단절(Idle Disconnect) 대응
AWS RDS 다중 AZ Failover, Aurora 스위치오버, 클라우드 NAT 게이트웨이의 TCP 유휴 연결 정리로 인해 발생하는 연결 끊김 현상에 대한 대응책입니다.

1. **`pool_pre_ping=True` (좀비 커넥션 자동 퇴출)**:
   - 풀에서 커넥션을 체크아웃할 때 경량 핑(PostgreSQL/MySQL: `SELECT 1`)을 데이터베이스로 전송합니다.
   - 만약 커넥션이 서버 측에서 이미 종료된 상태라면 에러를 발생시키지 않고 조용히 연결을 버린 뒤, 신규 커넥션을 즉시 수립하여 사용자 요청에 할당합니다.
2. **`pool_recycle=1800` (정기적인 커넥션 재생성)**:
   - 커넥션의 사용 시간이 1,800초(30분)를 초과하면 다음 반환 시점에 자동으로 해당 커넥션을 닫고 새 연결을 준비합니다.
   - 중간 방화벽(L4 스위치)이 비활성 TCP 커넥션을 일방적으로 Drop하여 발생하는 `server closed the connection unexpectedly` 에러를 사전에 방지합니다.

### 4.3 프로세스 수명주기 및 컨테이너 롤링 배포 시 자원 회수
1. **동기식 프로세스 자동 종료 (`atexit`)**:
   - `DatabaseManager.__init__`에서 `atexit.register(self.dispose)`가 자동 등록됩니다.
   - 컨테이너 SIGTERM 또는 프로세스 종료 시 열려 있는 동기 SQLAlchemy 엔진 커넥션 풀을 정상 반환하여 DB 서버 세션 잔류를 방지합니다.
2. **비동기 런타임(FastAPI / Starlette) Lifespan 종료 훅 구현**:
   - 비동기 AsyncEngine은 이벤트 루프가 닫히기 전에 풀을 정리해야 합니다. ASGI Lifespan 컨텍스트에서 `await db.async_dispose()`를 명시적으로 호출해야 합니다.
   ```python
   from contextlib import asynccontextmanager
   from fastapi import FastAPI
   from sqla_autoconfig import db

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # 애플리케이션 시작 단계
       yield
       # 컨테이너 SIGTERM 수신 및 롤링 배포 시 커넥션 풀 안전 회수
       await db.async_dispose()

   app = FastAPI(lifespan=lifespan)
   ```
