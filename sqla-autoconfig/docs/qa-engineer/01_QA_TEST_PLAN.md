# [sqla-autoconfig] 통합 QA 테스트 계획서 (QA Test Plan)

- **작성일자**: 2026-09-22
- **작성자**: 품질 보증 엔지니어 (`qa-engineer`)
- **문서 버전**: v1.1 (Humanizer 지침 기반 전면 개정)
- **상태**: **Approved**

---

## 1. 테스트 목적 및 중점 검증 영역 (Focus Areas)

데이터베이스 연동 계층은 백엔드 서비스의 가용성과 데이터 무결성을 결정짓는 가장 취약한 영역입니다. 단순 CRUD 테스트 통과만으로는 프로덕션 환경의 고부하 상황을 보장할 수 없습니다. 실무에서 빈번히 겪는 장애는 주로 다음에서 기인합니다:

1. **커넥션 누수(Connection Pool Leak)**: 예외 발생 시 트랜잭션 롤백은 되었으나 커넥션이 풀에 반환되지 않아 점진적으로 풀이 고갈되고 서비스 전체가 먹통이 되는 현상.
2. **크리덴셜 특수문자로 인한 DSN 파싱 장애**: 패스워드에 `@`, `:`, `#`, `/` 등 예약 문자가 포함되어 SQLAlchemy DSN 파서가 호스트명을 잘못 인식하여 부팅 실패.
3. **고동시성 세션 경합 및 데드락**: 수십 개의 스레드나 비동기 코루틴이 동시 진입할 때 커넥션 획득 대기 큐에서 타임아웃이 발생하거나 스레드 간 세션 오염이 발생하는 문제.
4. **FastAPI 웹 프레임워크 수명 주기 결합**: 엔드포인트에서 4xx/5xx `HTTPException`이 발생해도 제너레이터의 `finally` 구문을 통해 세션이 정상적으로 닫히고 풀로 복귀하는지 여부.

본 QA 테스트 계획서는 이러한 실무 장애 패턴을 사전에 차단하기 위해 수립되었으며, 설정 로딩부터 드라이버 매핑, 트랜잭션 롤백 무결성, 50 스레드 / 100 코루틴 부하 상황에서의 리소스 누수 여부를 중점 검증합니다.

---

## 2. 테스트 환경 및 제약 조건

- **런타임 및 플랫폼**:
  - Python: `3.11.9` (호환 범위: `3.10 ~ 3.13`)
  - OS: macOS (darwin arm64) 및 Linux (Ubuntu 22.04 LTS x86_64)
- **핵심 라이브러리 스펙**:
  - ORM 엔진: `SQLAlchemy >= 2.0.38` (2.0 스타일 세션 및 `AsyncSession`)
  - 스키마 검증: `pydantic >= 2.10.6`
  - 지원 RDBMS 드라이버:
    - PostgreSQL: `psycopg2-binary` (동기), `asyncpg` (비동기)
    - MySQL/MariaDB: `pymysql` (동기), `aiomysql` (비동기)
    - SQLite: 내장 `sqlite3` (동기), `aiosqlite` (비동기)
- **테스트 격리 방안**:
  - 단위 및 동시성 테스트는 파일 기반 SQLite 및 격리된 인메모리 테스트 환경을 구성하여 외부 DB 인프라 의존 없이 독립적으로 재현 가능하도록 설계합니다.
  - 계층형 설정 로더 검증은 `tmp_path`를 활용한 임시 YAML/JSON 파일 생성과 `monkeypatch`를 통한 OS 환경변수 격리를 적용합니다.

---

## 3. 장애 시나리오 중심 테스트 매트릭스 (Test Matrix)

| 케이스 ID | 검증 도메인 | 장애 및 엣지 시나리오 | 사전 조건 및 입력 데이터 | 기대 결과 및 패스 기준 (Pass Criteria) |
| :--- | :---: | :--- | :--- | :--- |
| **`TC-CFG-001`** | 계층형 설정 | 동일 설정 키가 환경변수, YAML, JSON에 중복 정의된 경우 | `DB_HOST`를 환경변수(`env_host`), YAML(`yaml_host`), JSON(`json_host`)에 동시 주입 | 우선순위(`kwargs > ENV > YAML > JSON > Defaults`)에 따라 `env_host`가 채택되고 하위 파일의 미중복 키만 병합 |
| **`TC-CFG-002`** | 크리덴셜 보안 | 패스워드에 URL 예약 특수문자(`@`, `:`, `#`, `/`) 포함 | 패스워드: `p@ss:w/ord#123` 주입 | DSN 빌드 시 `quote_plus` 처리가 자동으로 적용되어 호스트명 오인 파싱 에러 방지 |
| `TC-CFG-003` | 설정 Fail-Fast | 미지원 다이얼렉트명 또는 유효 범위를 벗어난 포트 번호 주입 | `db_type="oracle"`, `port=99999` 주입 | 애플리케이션 부팅 즉시 `ConfigurationValidationError` 발생 및 원인 필드 명시 |
| **`TC-DRV-001`** | 드라이버 매핑 | PostgreSQL, MySQL, SQLite 동기/비동기 드라이버 자동 결합 | 각 RDBMS 타입 및 `async_mode=True/False` 플래그 설정 | PostgreSQL 비동기 시 `postgresql+asyncpg`, MySQL 시 `mysql+aiomysql` 등 올바른 DSN 스킴 생성 |
| `TC-DRV-002` | 확장성 | 외부 플러그인용 신규 다이얼렉트 동적 등록 | `DialectRegistry.register("cockroachdb", "cockroachdb", "cockroachdb+asyncpg")` | 런타임에 안전하게 레지스트리에 등록되고 엔진 생성 시 해당 드라이버 활용 가능 |
| **`TC-TX-001`** | 트랜잭션 롤백 | 동기 트랜잭션 블록 내에서 런타임 예외 발생 | `with db.transaction() as s:` 내부에서 DB 삽입 후 강제 `ValueError` 발생 | 예외 발생 즉시 Rollback되어 DB에 더티 데이터가 잔류하지 않으며, 세션은 안전하게 풀로 반환 |
| `TC-TX-002` | 정상 커밋 | 동기 트랜잭션 블록 정상 완료 | 블록 내 데이터 삽입 후 정상 탈출 | 블록 종료 시점에 자동 `commit()` 호출 및 커넥션 반환 확인 |
| **`TC-ATX-001`** | 비동기 롤백 | 비동기 코루틴 트랜잭션 내에서 예외 발생 | `async with db.async_transaction() as s:` 내부에서 강제 `RuntimeError` | 비동기 커넥션 레벨에서 안전하게 Rollback 수행 및 리소스 회수 |
| `TC-ATX-002` | 비동기 커밋 | 비동기 코루틴 트랜잭션 정상 완료 | 비동기 레코드 삽입 후 정상 탈출 | 자동 `commit()` 완료 및 세션 정리 |
| **`TC-FAST-001`** | FastAPI 연동 | 엔드포인트 핸들러 처리 중 예외 발생 시 세션 반환 | `get_db()`, `get_async_db()` 제너레이터 실행 중 핸들러 예외 시뮬레이션 | 제너레이터의 `finally` 구문이 실행되어 세션이 닫히고 풀로 복귀함을 검증 (FastAPI 의존성 누수 방지) |
| **`TC-DEC-001`** | 데코레이터 | `@transactional` 및 `@async_transactional` 적용 함수 검증 | `session=None` 파라미터를 가진 동기/비동기 함수 호출 | 활성 트랜잭션 세션이 자동 주입되고, 정상 종료 시 커밋, 예외 시 롤백 수행 후 원래 예외를 호출자에게 투명하게 전파 |
| **`TC-CONC-001`** | 고동시성 스레드 | 50개 스레드가 커넥션 풀을 동시 경합 | `ThreadPoolExecutor(max_workers=15)`, 50개 동시 트랜잭션 삽입 | 교착(Deadlock)이나 Timeout 없이 50건 전수 커밋 성공 및 커넥션 풀 누수 0개 확인 |
| `TC-CONC-002` | 고동시성 코루틴 | 100개 비동기 코루틴이 커넥션 풀을 동시 경합 | `asyncio.gather`로 100개 코루틴 동시 실행 | 비동기 세션 간 충돌(Race Condition) 없이 100건 전수 정상 커밋 및 리소스 해제 확인 |
| `TC-ENG-001` | 풀 파라미터 | 커넥션 풀 설정값 (`pool_size`, `max_overflow`, `pool_recycle`) 전달 | `pool_size=10`, `max_overflow=20`, `pool_recycle=3600` 명시 | SQLAlchemy 엔진 생성 시 해당 옵션이 정확히 전달되고 첫 쿼리 시점까지 지연 초기화(Lazy Init) 유지 |

---

## 4. 합격 기준 및 출시 조건 (Exit Criteria)

1. **테스트 통과율 100%**: 작성된 25개 테스트 케이스 전수 무결점 통과 (0 Failure, 0 Error).
2. **코드 커버리지 85% 이상**: 패키지 전체 라인 커버리지 88% 이상 달성 (방어적 fallback 제외한 핵심 로직 전수 커버).
3. **결함 허용 기준**: Blocker 0건, Critical 0건, Minor 0건.
4. **핵심 신뢰성 검증**:
   - 트랜잭션 블록 내 예외 발생 시 100% 롤백 보장.
   - 50 스레드 / 100 코루틴 부하 상태에서 커넥션 풀 누수(Leak) 0건 입증.
   - 크리덴셜 특수문자 안전 인코딩 검증 완료.
