# [sqla-autoconfig] 통합 QA 테스트 계획서 (QA Test Plan)

- **작성일자**: 2026-09-22
- **작성자**: 통합 품질 보증 엔지니어 (`qa-engineer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. 테스트 범위 및 환경 (Test Scope & Environment)
- **테스트 대상**: `sqla-autoconfig` 파이썬 패키지 전 기능
  - 계층형 설정 로더 (환경변수, YAML, JSON, 명시적 인자) 우선순위 검증
  - 다중 RDBMS 다이얼렉트 (PostgreSQL, MySQL, MariaDB, SQLite) 드라이버 매핑 및 확장성
  - 커넥션 풀 파라미터 주입 및 지연 초기화(Lazy Init)
  - 동기 및 비동기 세션/트랜잭션 컨텍스트 매니저 (Commit & Rollback)
  - 선언적 선언적 트랜잭션 데코레이터 (`@transactional`, `@async_transactional`)
  - FastAPI 동기/비동기 의존성 주입 연동 (`get_db`, `get_async_db`)
  - 대규모 동접(High-concurrency) 스레드 및 코루틴 풀 안정성 및 리소스 누수(Zero-Leak)
- **테스트 환경**:
  - Python 런타임: Python 3.11 (macOS aarch64)
  - SQLAlchemy 버전: 2.0.54
  - Pydantic 버전: 2.13.5
  - 드라이버: `psycopg2-binary`, `asyncpg`, `pymysql`, `aiomysql`, `aiosqlite`
  - 테스트 프레임워크: pytest 9.1.1, pytest-asyncio, pytest-cov

---

## 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 케이스 ID | 테스트 구분 | 검증 시나리오 | 사전 조건 및 입력 데이터 | 기대 결과 (Pass Criteria) |
| :--- | :---: | :--- | :--- | :--- |
| `TC-CFG-001` | 설정 계층 | 환경변수 > YAML > JSON > Defaults 우선순위 병합 | JSON, YAML 동시 작성 및 환경변수 주입 | 환경변수 값이 최우선 적용되고 누락된 키만 하위 파일에서 상속 |
| `TC-CFG-002` | 보안/인코딩 | 패스워드 특수문자(`@`, `:`, `#`, `/`) 포함 시 URL 빌드 | 패스워드: `p@ss:w/ord#123` | URL 생성 시 안전하게 `quote_plus` 인코딩되어 파싱 에러 방지 |
| `TC-DRV-001` | 드라이버 | PostgreSQL, MySQL, MariaDB 동기/비동기 매핑 | `db_type="postgres"`, `async_mode=True` | `postgresql+asyncpg` 정확히 조합 |
| `TC-DRV-002` | 확장성 | 신규 다이얼렉트 동적 등록 (`DialectRegistry.register`) | 신규 다이얼렉트 `cockroachdb` 등록 | 정상 등록 및 URL 생성 성공 |
| `TC-TX-001`  | 트랜잭션 | 동기 트랜잭션 정상 커밋 | `with db.transaction() as s:` 데이터 삽입 | 블록 정상 종료 시 자동 commit 완료 |
| `TC-TX-002`  | 트랜잭션 | 동기 트랜잭션 예외 발생 시 자동 롤백 | 블록 내에서 강제 `ValueError` 발생 | 데이터 롤백되어 DB에 반영되지 않음 |
| `TC-ATX-001` | 비동기 트랜잭션 | 비동기 트랜잭션 정상 커밋 | `async with db.async_transaction() as s:` | 자동 commit 완료 |
| `TC-ATX-002` | 비동기 트랜잭션 | 비동기 트랜잭션 예외 발생 시 자동 롤백 | 블록 내에서 강제 `RuntimeError` 발생 | 데이터 롤백 완료 |
| `TC-FAST-001`| 웹 통합 | FastAPI 의존성 주입 (`get_db`, `get_async_db`) | 제너레이터 호출 및 세션 사용 후 종료 | `finally`에서 세션 및 커넥션 안전 반환 |
| `TC-DEC-001` | 데코레이터 | `@transactional` 및 `@async_transactional` 세션 주입 | 함수 인자에 `session=None` 선언 | 트랜잭션 세션 자동 주입 및 실행 후 자동 커밋 |
| `TC-CONC-001`| 동시성 부하 | 50개 동시 스레드 트랜잭션 스트레스 테스트 | ThreadPoolExecutor 15 workers, 50 작업 | 교착 없이 50건 전수 삽입 및 누수 0 |
| `TC-CONC-002`| 동시성 부하 | 100개 동시 비동기 코루틴 스트레스 테스트 | `asyncio.gather` 100개 코루틴 | 교착 없이 100건 전수 삽입 및 누수 0 |
