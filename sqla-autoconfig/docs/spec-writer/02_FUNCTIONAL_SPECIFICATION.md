# [sqla-autoconfig] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-23
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.1 (Humanizer 지침 반영 개정판)
- **상태**: Approved

---

## 1. 기능 계층 구조도 (Feature Hierarchy Tree)

`sqla-autoconfig` 패키지의 전체 기능 구조는 데이터베이스 연동 및 트랜잭션 수명 주기를 책임지는 4개 엔지니어링 모듈로 구분됩니다.

```
[1Depth: sqla-autoconfig]
  ├── [2Depth: 설정 관리 (Cascading Configuration)]
  │     ├── [3Depth: 계층형 다중 설정 로더 및 자동 병합] (FUNC-CFG-001)
  │     └── [3Depth: Pydantic 기반 DB 설정 유효성 검증 및 URL 빌드] (FUNC-CFG-002)
  ├── [2Depth: 다이얼렉트 및 드라이버 (Dialects & Drivers)]
  │     ├── [3Depth: PostgreSQL/MySQL/MariaDB 동기·비동기 자동 매핑] (FUNC-DRV-001)
  │     └── [3Depth: 커스텀 다이얼렉트 플러그인 확장 레지스트리] (FUNC-DRV-002)
  ├── [2Depth: 커넥션 풀 & 엔진 (Engine & Pool Lifecycle)]
  │     ├── [3Depth: SQLAlchemy 2.0 동기/비동기 엔진 자동 빌드] (FUNC-ENG-001)
  │     └── [3Depth: 고신뢰성 커넥션 풀 최적화 및 atexit 안전 회수] (FUNC-ENG-002)
  └── [2Depth: 세션 및 트랜잭션 (Session & Transaction)]
        ├── [3Depth: 자동 롤백 및 풀 반환 트랜잭션 컨텍스트 매니저] (FUNC-CTX-001)
        ├── [3Depth: 선언적 트랜잭션 데코레이터] (FUNC-CTX-002)
        └── [3Depth: FastAPI 의존성 주입 연동 헬퍼 (get_db / get_async_db)] (FUNC-CTX-003)
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

모든 단위 기능의 세부 스펙, 8대 데이터 항목 명세, 비즈니스 규칙 및 예외 처리 가이드는 [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md)에 상세 기술되어 있습니다.

| 기능 ID | 1Depth (영역) | 2Depth (모듈) | 3Depth (단위기능명) | 우선순위 | 대응 요구사항 ID | 상세 명세 링크 |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `FUNC-CFG-001` | 설정 관리 | 설정 로더 | 계층형 설정 로더 및 자동 병합 (ENV > YAML > JSON > Defaults) | Must | `REQ-CFG-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-cfg-001`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-cfg-001) |
| `FUNC-CFG-002` | 설정 관리 | 스키마 검증 | Pydantic 기반 DB 설정 검증 및 비밀번호 특수문자 안전 인코딩 | Must | `REQ-CFG-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-cfg-002`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-cfg-002) |
| `FUNC-DRV-001` | 드라이버 | 다이얼렉트 | Postgres/MySQL/MariaDB 동기·비동기 URL 자동 변환 | Must | `REQ-DRV-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-drv-001`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-drv-001) |
| `FUNC-DRV-002` | 드라이버 | 확장 레지스트리 | DialectRegistry 플러그인 등록 인터페이스 | Should | `REQ-DRV-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-drv-002`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-drv-002) |
| `FUNC-ENG-001` | 커넥션 풀 | 엔진 팩토리 | SQLAlchemy 2.0 동기/비동기 엔진 및 세션메이커 자동 구성 | Must | `REQ-POOL-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-eng-001`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-eng-001) |
| `FUNC-ENG-002` | 커넥션 풀 | 풀 라이프사이클 | `pool_pre_ping`/`recycle` 튜닝 및 `atexit` 안전 풀 해제 | Must | `REQ-POOL-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-eng-002`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-eng-002) |
| `FUNC-CTX-001` | 세션/트랜잭션 | 컨텍스트 | `with db.transaction()`, `async with db.async_transaction()` | Must | `REQ-CTX-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-001`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-001) |
| `FUNC-CTX-002` | 세션/트랜잭션 | 데코레이터 | 선언적 트랜잭션 데코레이터 (`@db.transactional`) | Should | `REQ-DEC-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-002`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-002) |
| `FUNC-CTX-003` | 세션/트랜잭션 | 프레임워크 연동 | FastAPI `Depends(db.get_db)` / `Depends(db.get_async_db)` 지원 | Should | `REQ-INT-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-003`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-003) |

---

## 3. 상세 명세 문서 맵 (Modular FSD Map)

- [sqla-autoconfig 코어 상세기능정의서 (Modular FSD)](./fsd/AUTOCONFIG_SPECIFICATION.md)
  - 핵심 단위기능 9건에 대해 7대 상세 명세 및 데이터 항목 표를 완비하여 기술합니다.
