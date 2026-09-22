# [sqla-autoconfig] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-22
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. 기능 계층 구조도 (Feature Hierarchy Tree)

```
[1Depth: sqla-autoconfig]
  ├── [2Depth: 설정 관리 (Configuration)]
  │     ├── [3Depth: 계층형 설정 로더 및 병합] (FUNC-CFG-001)
  │     └── [3Depth: 설정 스키마 및 유효성 검증] (FUNC-CFG-002)
  ├── [2Depth: 드라이버 및 다이얼렉트 (Dialects)]
  │     ├── [3Depth: PostgreSQL/MySQL/MariaDB 드라이버 매핑] (FUNC-DRV-001)
  │     └── [3Depth: 커스텀 다이얼렉트 레지스트리 확장] (FUNC-DRV-002)
  ├── [2Depth: 커넥션 풀 & 엔진 (Pool & Engine)]
  │     ├── [3Depth: 고성능 동기/비동기 엔진 자동 생성] (FUNC-ENG-001)
  │     └── [3Depth: 대규모 동접 커넥션 풀 튜닝 및 라이프사이클 관리] (FUNC-ENG-002)
  └── [2Depth: 세션 & 트랜잭션 관리 (Session & Transaction)]
        ├── [3Depth: 안전한 세션/트랜잭션 컨텍스트 매니저] (FUNC-CTX-001)
        ├── [3Depth: 선언적 트랜잭션 데코레이터] (FUNC-CTX-002)
        └── [3Depth: 웹 프레임워크(FastAPI 등) 의존성 주입 지원] (FUNC-CTX-003)
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

모든 단위 기능은 도메인별 상세기능정의서([`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md))에 7대 상세 명세가 완비되어 있습니다.

| 기능 ID | 1Depth (도메인) | 2Depth (모듈) | 3Depth (단위기능명) | 우선순위 | 대응 요구사항 ID | 상세 명세 문서 링크 |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `FUNC-CFG-001` | 설정 관리 | 설정 로더 | 계층형 설정 로더 및 병합 (ENV > YAML > JSON > Defaults) | Must | `REQ-CFG-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-cfg-001) |
| `FUNC-CFG-002` | 설정 관리 | 설정 유효성 | Pydantic 기반 DB 연결 설정 스키마 검증 | Must | `REQ-CFG-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-cfg-002) |
| `FUNC-DRV-001` | 드라이버 | 다이얼렉트 | Postgres/MySQL/MariaDB 동기/비동기 URL 자동 변환 | Must | `REQ-DRV-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-drv-001) |
| `FUNC-DRV-002` | 드라이버 | 확장성 | DialectRegistry 플러그인 등록 인터페이스 | Should | `REQ-DRV-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-drv-002) |
| `FUNC-ENG-001` | 커넥션 풀 | 엔진 팩토리 | Sync/Async SQLAlchemy 2.0 엔진 자동 빌드 | Must | `REQ-POOL-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-eng-001) |
| `FUNC-ENG-002` | 커넥션 풀 | 풀 튜닝 | 고동시성 무장애 풀 파라미터 적용 및 리소스 해제 | Must | `REQ-POOL-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-eng-002) |
| `FUNC-CTX-001` | 세션/트랜잭션 | 컨텍스트 | `with db.transaction()`, `async with db.async_transaction()` | Must | `REQ-CTX-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-001) |
| `FUNC-CTX-002` | 세션/트랜잭션 | 데코레이터 | `@db.transactional`, `@db.async_transactional` | Should | `REQ-DEC-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-002) |
| `FUNC-CTX-003` | 세션/트랜잭션 | 프레임워크 연동| FastAPI `Depends(db.get_db)` / `Depends(db.get_async_db)` | Should | `REQ-INT-001` | [`fsd/AUTOCONFIG_SPECIFICATION.md`](./fsd/AUTOCONFIG_SPECIFICATION.md#func-ctx-003) |

---

## 3. 도메인별 분할 명세서 맵 (Modular FSD Map)

- [sqla-autoconfig 코어 상세기능정의서](./fsd/AUTOCONFIG_SPECIFICATION.md)
