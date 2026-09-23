# [sqla-autoconfig] 백엔드 TDD 사이클 실행 기록서 (Backend TDD Log)

- **작성일자**: 2026-09-22
- **작성자**: 백엔드 TDD 엔지니어 (`backend-tdd-engineer`)
- **문서 버전**: v1.1 (Humanizer 스킬 적용 개정본)
- **상태**: Approved

---

## 1. TDD 개발 개요 및 엔지니어링 목표

SQLAlchemy 2.0 기반의 데이터베이스 연동 코드는 매 프로젝트마다 반복되는 보일러플레이트(엔진 생성, 풀 튜닝, 세션/트랜잭션 라이프사이클 관리, FastAPI 의존성 주입 등)가 많습니다. 특히 동기/비동기 드라이버를 혼용하거나 특수문자가 섞인 비밀번호로 DSN을 조합할 때 예기치 않은 런타임 장애가 자주 발생합니다.

`sqla-autoconfig`의 개발 목표는 다음과 같습니다:
1. **계층형 우선순위 설정 (`kwargs > ENV > YAML > JSON > Defaults`)**: 환경에 따라 유연하게 데이터베이스 설정을 주입.
2. **동기/비동기 듀얼 드라이버 지원**: PostgreSQL(`psycopg2`/`asyncpg`), MySQL(`pymysql`/`aiomysql`), SQLite(`sqlite3`/`aiosqlite`)를 일관된 인터페이스로 제어.
3. **고동시성 무누수 커넥션 풀링**: `QueuePool` 및 `AsyncAdaptedQueuePool` 파라미터를 정밀하게 튜닝하고, 프로세스 종료 훅(`atexit`)과 컨텍스트 매니저를 통해 체크아웃된 소켓이 유실되지 않도록 보장.
4. **선언적 트랜잭션 전파**: `@transactional` 및 `@async_transactional` 데코레이터를 통해 세션 자동 주입 및 트랜잭션 커밋/롤백 생명주기를 투명하게 관리.

모든 기능은 `tests/` 디렉토리 아래 실패하는 테스트를 먼저 작성(RED)하고, 이를 통과시키는 최소 구현(GREEN)을 작성한 뒤, 실무 관점에서 안정성을 높이는 리팩토링(REFACTOR) 과정을 거쳤습니다.

---

## 2. Red-Green-Refactor 사이클 실행 기록

### [Cycle 1] 계층형 설정 로더 및 Pydantic v2 스키마 검증
- **대상 파일**: [`sqla_autoconfig/config.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/config.py), [`sqla_autoconfig/exceptions.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/exceptions.py)
- **테스트 파일**: [`tests/test_config.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/tests/test_config.py)

#### 1. RED Phase (실패하는 테스트 작성)
데이터베이스 설정 모델인 `DatabaseSettings`와 설정 로더 `ConfigLoader`가 아직 존재하지 않는 상태에서 테스트를 작성했습니다.

- **작성한 테스트 시나리오**:
  - `test_env_overrides_yaml_and_json`: `DB_HOST`, `DB_PORT`, `DB_PASSWORD` 등 환경변수가 설정 파일의 값보다 우선 적용되는지 검증.
  - `test_password_special_character_url_encoding`: 비밀번호에 `@`, `/`, `:`, `?` 등 URL 예약어가 포함되어 있을 때 DSN 생성 시 `quote_plus` 처리가 되지 않으면 파싱 오류가 발생하는 문제 검증.
  - `test_invalid_port_validation`: 포트 번호가 1 미만이거나 65535를 초과할 때 `ValidationError`가 발생하는지 검증.
  - `test_unsupported_dialect_raises_error`: 지원하지 않는 다이얼렉트(`oracle` 등) 지정 시 `UnsupportedDialectError` 발생 여부 검증.

- **실행 결과 (실패 확인)**:
```
ImportError while importing test module 'tests/test_config.py'
E   ModuleNotFoundError: No module named 'sqla_autoconfig.config'
FAILED tests/test_config.py - 1 error during collection
```

#### 2. GREEN Phase (최소 구현으로 통과)
- `sqla_autoconfig/exceptions.py`에 `SqlaAutoconfigError`, `UnsupportedDialectError`, `ConfigurationValidationError`를 정의했습니다.
- `sqla_autoconfig/config.py`에 Pydantic v2의 `BaseModel`을 상속하는 `DatabaseSettings`를 작성했습니다.
- 비밀번호 인코딩 이슈를 해결하기 위해 DSN 조합 프로퍼티(`sync_url`, `async_url`) 내에서 `urllib.parse.quote_plus(self.password)`를 명시적으로 적용했습니다.
- `ConfigLoader`에 `_deep_merge` 메서드를 추가하고, `Defaults -> JSON -> YAML -> ENV -> kwargs` 순서로 덮어쓰도록 최소 병합 루프를 구현했습니다.

- **실행 결과 (성공 확인)**:
```
tests/test_config.py .......                                             [100%]
7 passed in 0.12s
```

#### 3. REFACTOR Phase (구조 개선 및 엔지니어링 고민)
- **발견된 문제점**: `ConfigLoader.load()` 호출 시 로컬 개발 디렉토리에 존재하는 실제 `config.yaml`이나 `.env` 파일이 테스트 실행 시 의도치 않게 로드되어 격리성을 깨뜨리는 현상이 있었습니다.
- **개선 작업**: `ConfigLoader.load(filenames_override=...)` 파라미터를 추가하여 단위 테스트 실행 시 임시 디렉토리(`tmp_path`)의 파일만 정확히 바라보도록 제어했습니다.
- **타입 힌트 강화**: DSN 생성 프로퍼티에서 SQLite의 경우 `sqlite:///relative/path` 또는 `sqlite:////absolute/path`처럼 슬래시 개수가 달라지는 특성을 분기 처리하여 드라이버 경로 파싱 예외를 사전에 차단했습니다.

---

### [Cycle 2] RDBMS 다이얼렉트 매핑 및 레지스트리
- **대상 파일**: [`sqla_autoconfig/dialects.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/dialects.py)
- **테스트 파일**: [`tests/test_dialects.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/tests/test_dialects.py)

#### 1. RED Phase (실패하는 테스트 작성)
각 데이터베이스 엔진별 동기/비동기 드라이버 조합(`postgresql+psycopg2` vs `postgresql+asyncpg`, `mysql+pymysql` vs `mysql+aiomysql`)을 자동 판별하는 매핑 레지스트리 검증 테스트를 작성했습니다.

- **작성한 테스트 시나리오**:
  - `test_builtin_dialects_mapping`: PostgreSQL, MySQL, MariaDB, SQLite에 대해 동기 드라이버와 비동기 드라이버 명칭이 정확히 매핑되는지 검증.
  - `test_custom_dialect_registration`: 신규 또는 사내 커스텀 드라이버(예: `cockroachdb`)를 `DialectRegistry.register()`로 동적 추가할 수 있는지 검증.
  - `test_get_unregistered_dialect`: 등록되지 않은 드라이버 요청 시 `UnsupportedDialectError` 발생 여부 검증.

- **실행 결과 (실패 확인)**:
```
E   ModuleNotFoundError: No module named 'sqla_autoconfig.dialects'
FAILED tests/test_dialects.py - 1 error during collection
```

#### 2. GREEN Phase (최소 구현으로 통과)
- `DialectInfo` 데이터 클래스를 정의하여 `dialect`, `sync_driver`, `async_driver`, `default_port`를 묶었습니다.
- `DialectRegistry` 클래스에 내부 딕셔너리 `_registry: dict[str, DialectInfo]`를 두고, 클래스 로드 시점에 기본 지원 엔진들을 등록했습니다.
- 로컬 개발 및 단위 테스트 환경의 편의성을 위해 `sqlite`(`sqlite3` / `aiosqlite`)를 내장 드라이버로 기본 탑재했습니다.

- **실행 결과 (성공 확인)**:
```
tests/test_dialects.py ...                                               [100%]
3 passed in 0.02s
```

#### 3. REFACTOR Phase (구조 개선 및 엔지니어링 고민)
- **스레드 세이프티 확보**: `DialectRegistry.register()` 호출이 멀티스레드 환경에서 발생할 가능성을 고려해 `threading.Lock`으로 등록 루틴을 보호했습니다.
- **조회 방어 로직**: 입력된 dialect 문자열을 `.strip().lower()`로 정규화하여 사용자가 `PostgreSQL`이나 `POSTGRES`로 입력해도 정상적으로 매핑되도록 처리했습니다.

---

### [Cycle 3] 엔진 생성, 커넥션 풀 매니저 및 트랜잭션 컨텍스트
- **대상 파일**: [`sqla_autoconfig/manager.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/manager.py), [`sqla_autoconfig/context.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/context.py)
- **테스트 파일**: [`tests/test_manager.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/tests/test_manager.py), [`tests/test_context.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/tests/test_context.py)

#### 1. RED Phase (실패하는 테스트 작성)
실제 데이터베이스 커넥션을 맺고 세션을 관리하는 `DatabaseManager`와 `contextmanager` 기반의 세션 라이프사이클 테스트를 작성했습니다.

- **작성한 테스트 시나리오**:
  - `test_sync_transaction_commit_and_rollback`: 정상 종료 시 커밋, 블록 내부 예외 발생 시 자동 롤백 및 원본 예외 재전파 검증.
  - `test_async_transaction_commit_and_rollback`: 비동기(`async with`) 트랜잭션 블록의 동일 동작 검증.
  - `test_fastapi_dependencies`: FastAPI의 `Depends`로 사용할 `get_db`와 `get_async_db` 제너레이터가 요청 종료 후 세션을 확실히 `close()`하는지 검증.
  - `test_pool_arguments_forwarding`: `pool_size`, `max_overflow`, `pool_recycle`, `pool_pre_ping`, `pool_timeout` 설정이 SQLAlchemy `Engine.pool` 인스턴스에 누락 없이 반영되는지 검증.

- **실행 결과 (실패 확인)**:
```
E   ModuleNotFoundError: No module named 'sqla_autoconfig.manager'
FAILED tests/test_manager.py - 1 error during collection
FAILED tests/test_context.py - 1 error during collection
```

#### 2. GREEN Phase (최소 구현으로 통과)
- `sqla_autoconfig/manager.py`에 `DatabaseManager`를 구현하여 `create_engine`과 `create_async_engine`을 통해 `sessionmaker` / `async_sessionmaker` 팩토리를 생성했습니다.
- `sqla_autoconfig/context.py`에 동기 컨텍스트 매니저 `transaction()`, `session()` 및 비동기 컨텍스트 매니저 `async_transaction()`, `async_session()`을 구현했습니다.
- 각 컨텍스트 매니저 블록은 `try ... except: session.rollback(); raise ... finally: session.close()` 구조를 엄격히 적용했습니다.

- **실행 결과 (성공 확인)**:
```
tests/test_manager.py ..                                                 [100%]
tests/test_context.py ......                                             [100%]
8 passed in 0.18s
```

#### 3. REFACTOR Phase (구조 개선 및 엔지니어링 고민)
- **풀 누수(Leak) 방어 및 프로세스 종료 처리**: Python 인터프리터가 종료될 때 연결 풀 소켓이 OS 레벨에서 좀비로 남지 않도록 `atexit.register(self.dispose)`를 등록했습니다.
- **`pool_recycle`과 `pool_pre_ping` 기본값 정책**: 방화벽이나 클라우드 로드밸런서(AWS NLB, GCP ILB)의 유휴 타임아웃(보통 350초~3600초)으로 인한 `MySQL server has gone away` 또는 `RemoteDisconnected` 에러를 원천 차단하기 위해 `pool_recycle=1800`(30분), `pool_pre_ping=True`를 필수 기본값으로 강제했습니다.

---

### [Cycle 4] 선언적 트랜잭션 데코레이터 및 전역 싱글톤 인터페이스
- **대상 파일**: [`sqla_autoconfig/decorators.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/decorators.py), [`sqla_autoconfig/__init__.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/__init__.py)
- **테스트 파일**: [`tests/test_decorators.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/tests/test_decorators.py), [`tests/test_global_db.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/tests/test_global_db.py)

#### 1. RED Phase (실패하는 테스트 작성)
서비스 계층 함수에 붙여 트랜잭션을 제어하는 데코레이터와 전역 `db` 싱글톤 프록시 테스트를 작성했습니다.

- **작성한 테스트 시나리오**:
  - `test_transactional_decorator_injects_session`: 대상 함수 매개변수에 `session: Session`이 선언되어 있을 때 열린 세션을 자동으로 주입하는지 검증.
  - `test_transactional_decorator_joins_existing_session`: 호출자가 이미 활성화된 세션을 인자로 전달한 경우 새 트랜잭션을 열지 않고 기존 세션 컨텍스트에 참여(Propagation)하는지 검증.
  - `test_async_transactional_decorator`: 비동기 함수에 대해 동일한 세션 주입 및 트랜잭션 수명 제어가 작동하는지 검증.
  - `test_global_db_proxy_lazy_initialization`: `from sqla_autoconfig import db`로 임포트한 뒤 즉시 쿼리를 날려도 최초 접근 시점에 설정을 읽어 지연 초기화되는지 검증.

- **실행 결과 (실패 확인)**:
```
E   ImportError: cannot import name 'db' from 'sqla_autoconfig'
FAILED tests/test_global_db.py - 1 error during collection
FAILED tests/test_decorators.py - 1 error during collection
```

#### 2. GREEN Phase (최소 구현으로 통과)
- `inspect.signature`를 활용하여 대상 함수의 파라미터 목록 중 `session`이라는 이름이 존재하는지 확인하는 로직을 작성했습니다.
- `session` 파라미터가 없거나 호출자가 넘기지 않은 경우, 데코레이터 내부에서 `with db.transaction() as session:`을 열고 키워드 인자로 주입하도록 구현했습니다.
- `_GlobalDatabaseProxy` 클래스를 정의하고 `__getattr__`을 통해 내부 싱글톤 `DatabaseManager`로 호출을 위임하는 전역 `db` 인스턴스를 노출했습니다.

- **실행 결과 (성공 확인)**:
```
tests/test_decorators.py ....                                            [100%]
tests/test_global_db.py .                                                [100%]
5 passed in 0.14s
```

#### 3. REFACTOR Phase (구조 개선 및 엔지니어링 고민)
- **비동기 함수 오적용 방지**: `inspect.iscoroutinefunction(func)`를 검사하여 `@transactional`이 실수로 비동기 함수에 붙거나, 반대로 `@async_transactional`이 동기 함수에 붙었을 때 런타임에 명확한 `TypeError`를 던지도록 가드 로직을 추가했습니다.
- **메타데이터 보존**: `functools.wraps`를 엄격히 적용하여 FastAPI 라우트 핸들러나 Celery 태스크에서 함수의 `__name__`, `__doc__`, 어노테이션 정보가 유실되지 않도록 보장했습니다.

---

### [Cycle 5] 대규모 동접(High-concurrency) 풀 누수 및 스트레스 테스트
- **대상 파일**: [`sqla_autoconfig/manager.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/sqla_autoconfig/manager.py)
- **테스트 파일**: [`tests/test_concurrency.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig/tests/test_concurrency.py)

#### 1. RED Phase (실패하는 테스트 작성)
동시 요청이 쏟아지는 프로덕션 환경에서 커넥션 풀이 고갈되거나 세션이 제대로 반환되지 않는 누수 현상을 사전에 포착하기 위한 부하 테스트를 작성했습니다.

- **작성한 테스트 시나리오**:
  - `test_multithreaded_concurrency_stress`: 50개의 스레드가 동시에 `db.transaction()`을 열어 INSERT 및 SELECT를 수행할 때 데드락이나 세션 유실 없이 모두 통과하는지 검증.
  - `test_asyncio_concurrency_stress`: 100개의 비동기 코루틴이 `asyncio.gather`를 통해 동시에 세션을 획득하고 작업을 완료하는지 검증.
  - `Zero-Leak 검증`: 모든 작업 완료 후 `manager.sync_engine.pool.checkedout() == 0` 및 비동기 풀의 체크아웃 커넥션 수가 정확히 0인지 단언.

- **실행 결과 (초기 실행 시 발생한 실무 문제)**:
  SQLite 메모리/파일 DB를 대상으로 50개 스레드가 동시 접근할 때, 기본 저널 모드 설정으로 인해 `sqlite3.OperationalError: database is locked`가 발생하며 테스트가 실패했습니다.

#### 2. GREEN Phase (최소 구현으로 통과)
- 테스트 환경의 SQLite 엔진 생성 파라미터에 `connect_args={"timeout": 30}`을 전달하고, 동시성 테스트용 풀 파라미터(`pool_size=10, max_overflow=20, pool_timeout=30.0`)를 주입하여 스레드 대기 큐가 정상적으로 동작하도록 구성했습니다.
- 모든 스레드/코루틴이 작업을 마친 뒤 풀 상태를 검사하여 누수가 0임을 확인했습니다.

- **실행 결과 (성공 확인)**:
```
tests/test_concurrency.py ..                                             [100%]
2 passed in 0.38s
```

#### 3. REFACTOR Phase (구조 개선 및 엔지니어링 고민)
- **풀 타임아웃 예외 캡슐화**: 풀이 완전히 고갈되어 30초 대기 후 발생하는 `sqlalchemy.exc.TimeoutError`를 도메인 표준 예외인 `ConnectionPoolExhaustedError`로 매핑하여 호출자가 인프라 세부사항을 몰라도 대응할 수 있도록 구조를 개선했습니다.

---

## 3. 예외 및 엣지 케이스 테스트 매트릭스

| 테스트 함수명 | 테스트 시나리오 및 입력값 | 기대 동작 및 반환값 | 실무 검증 의의 |
| :--- | :--- | :--- | :---: |
| `test_password_special_characters` | 비밀번호에 `@p#s$w%o^r&d/` 등 특수문자 입력 | `quote_plus`로 인코딩된 안전한 DSN 생성 | DSN 파싱 오류로 인한 컨테이너 기동 실패 방지 |
| `test_invalid_port_range` | 포트 번호로 `-1` 또는 `70000` 입력 | Pydantic `ValidationError` 발생 | 잘못된 인프라 설정의 조기 감지(Fail-fast) |
| `test_unregistered_dialect` | 지원 목록에 없는 `oracle` 다이얼렉트 입력 | `UnsupportedDialectError` 발생 | 미지원 드라이버로 인한 런타임 Crash 방지 |
| `test_transaction_rollback_on_exception` | 트랜잭션 블록 내에서 인위적 `ValueError` 발생 | 데이터 롤백 및 원본 예외 호출자 재전파 | DB 원자성(Atomicity) 보장 및 데이터 오염 방지 |
| `test_pool_zero_leak_after_stress` | 100개 코루틴 동시 실행 후 풀 상태 조회 | `pool.checkedout() == 0` | 장기 실행 서비스의 파일 디스크립터 고갈 차단 |
| `test_atexit_engine_dispose` | 인터프리터 종료 시그널 발생 시뮬레이션 | 엔진의 모든 소켓 커넥션 일괄 close | 좀비 커넥션 및 DB 서버 리소스 낭비 차단 |

---

## 4. 최종 테스트 커버리지 및 실행 결과

```bash
$ .venv/bin/pytest --cov=sqla_autoconfig --cov-report=term-missing tests/
```

```
============================= test session starts ==============================
platform darwin -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/wonyoung/workspace/ozplayground/python-package/sqla-autoconfig
plugins: cov-7.1.0, asyncio-1.4.0
asyncio: mode=Mode.AUTO
collected 25 items

tests/test_concurrency.py ..                                             [  8%]
tests/test_config.py .......                                             [ 36%]
tests/test_context.py ......                                             [ 60%]
tests/test_decorators.py ....                                            [ 76%]
tests/test_dialects.py ...                                               [ 88%]
tests/test_global_db.py .                                                [ 92%]
tests/test_manager.py ..                                                 [100%]

================================ tests coverage ================================
Name                            Stmts   Miss  Cover   Missing
-------------------------------------------------------------
sqla_autoconfig/__init__.py        25      3    88%   48, 53-54
sqla_autoconfig/config.py         225     31    86%   41, 79, 177, 195, 206, 208, 211, 213, 231-232, 239-240, 247-248, 255-256, 269-270, 277-278, 288-289, 291-294, 296, 344-347
sqla_autoconfig/context.py         52      2    96%   29, 58
sqla_autoconfig/decorators.py      45     10    78%   30-31, 42-44, 66-67, 77-79
sqla_autoconfig/dialects.py        40      4    90%   45, 50-51, 60
sqla_autoconfig/exceptions.py      12      0   100%
sqla_autoconfig/manager.py         76      8    89%   126-129, 133-136
-------------------------------------------------------------
TOTAL                             475     58    88%
============================== 25 passed in 0.73s ==============================
```

- **총 테스트 수**: 25개 테스트 전원 통과 (0 failed, 0 broken)
- **전체 라인 커버리지**: **88%** (최소 목표치인 85% 상회)
- **실행 소요 시간**: 0.73초
