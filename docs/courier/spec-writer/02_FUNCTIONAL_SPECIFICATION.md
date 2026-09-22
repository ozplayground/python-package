# [courier] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-22
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. 기능 계층 구조도 (Feature Hierarchy Tree)

```
[1Depth: courier]
  ├── [2Depth: 응답 추상화 및 역직렬화 (Response & DTO)]
  │     ├── [3Depth: 통일된 제네릭 응답 ApiResponse[T]] (FUNC-RESP-001)
  │     └── [3Depth: Result 패턴 unwrap() 및 Pydantic into() 역직렬화] (FUNC-RESP-002)
  ├── [2Depth: 설정 관리 (Configuration)]
  │     ├── [3Depth: 계층형 다중 서비스 설정 로더 및 자동 병합] (FUNC-CONF-001)
  │     └── [3Depth: HTTP 클라이언트 스키마 유효성 검증] (FUNC-CONF-002)
  ├── [2Depth: 코어 클라이언트 엔진 (Core Engine & Connection Pool)]
  │     ├── [3Depth: HTTPX 기반 동기/비동기 코어 클라이언트] (FUNC-ENG-001)
  │     └── [3Depth: 커넥션 풀링 최적화 및 프로세스 라이프사이클 관리] (FUNC-ENG-002)
  ├── [2Depth: 회복성 및 재시도 (Resilience & Retry)]
  │     ├── [3Depth: 지수 백오프 및 지터(Jitter) 스마트 리트라이] (FUNC-RETY-001)
  │     └── [3Depth: HTTP 상태 코드 및 예외 기반 재시도 조건 판별] (FUNC-RETY-002)
  └── [2Depth: 보안 및 관측성 (Security & Observability)]
        ├── [3Depth: 서비스별 인증 헤더/토큰 자동 주입 인터셉터] (FUNC-AUTH-001)
        └── [3Depth: 민감 정보 마스킹 및 구조화 로깅/레이턴시 측정] (FUNC-LOG-001)
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

모든 단위 기능은 도메인별 상세기능정의서([`fsd/HTTP_CLIENT_SPECIFICATION.md`](./fsd/HTTP_CLIENT_SPECIFICATION.md))에 7대 상세 명세가 완비되어 있습니다.

| 기능 ID | 1Depth (도메인) | 2Depth (모듈) | 3Depth (단위기능명) | 우선순위 | 대응 요구사항 ID | 상세 명세 문서 링크 |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `FUNC-RESP-001` | 응답 추상화 | 응답 래퍼 | 통일된 제네릭 응답 모델 `ApiResponse[T]` | Must | `REQ-RESP-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-001) |
| `FUNC-RESP-002` | 응답 추상화 | DTO 변환 | Result 패턴 `unwrap()` 및 Pydantic `into()` 자동 역직렬화 | Must | `REQ-DTO-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-002) |
| `FUNC-CONF-001` | 설정 관리 | 설정 로더 | 다중 서비스 계층형 설정 로더 (ENV > YAML > JSON > Defaults) | Must | `REQ-CONF-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-001) |
| `FUNC-CONF-002` | 설정 관리 | 스키마 검증 | Pydantic 기반 HTTP 클라이언트 설정 유효성 검증 및 기본값 주입 | Must | `REQ-CONF-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-002) |
| `FUNC-ENG-001` | 코어 엔진 | 클라이언트 | HTTPX 코어 클라이언트 (동기/비동기 동시 지원 인터페이스) | Must | `REQ-ENG-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-001) |
| `FUNC-ENG-002` | 코어 엔진 | 커넥션 풀 | 고동시성 무누수 커넥션 풀링 최적화 및 `atexit` 안전 해제 | Must | `REQ-ENG-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-002) |
| `FUNC-RETY-001` | 회복성 | 재시도 엔진 | 지수 백오프(Exponential Backoff) 및 지터(Jitter) 스마트 리트라이 | Must | `REQ-RETY-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-001) |
| `FUNC-RETY-002` | 회복성 | 재시도 판별 | HTTP 429/5xx 상태코드 및 네트워크 타임아웃 판별기 | Must | `REQ-RETY-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-002) |
| `FUNC-AUTH-001` | 보안/인증 | 인터셉터 | Bearer Token 및 API Key 인증 헤더 자동 주입 인터셉터 | Should | `REQ-AUTH-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-auth-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-auth-001) |
| `FUNC-LOG-001` | 관측성 | 로깅/메트릭 | 민감 정보 마스킹 및 구조화 로깅 / 레이턴시 추적 | Should | `REQ-LOG-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-log-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-log-001) |

---

## 3. 도메인별 분할 명세서 맵 (Modular FSD Map)

- [HTTP 클라이언트 및 응답 자동 구성 상세기능정의서 (Modular FSD)](./fsd/HTTP_CLIENT_SPECIFICATION.md)
  - `FUNC-RESP-001`: 통일된 응답 `ApiResponse[T]`
  - `FUNC-CONF-001`: 계층형 설정 로더 및 서비스별 클라이언트 획득
  - `FUNC-ENG-001`: HTTPX 코어 클라이언트 (동기 및 비동기 엔진)
  - `FUNC-RETY-001`: 지수 백오프 및 지터(Jitter) 스마트 리트라이
  - `FUNC-RESP-002`: DTO 자동 역직렬화 및 Result 체이닝
  - `FUNC-CONF-002`: 설정 유효성 검증
  - `FUNC-ENG-002`: 커넥션 풀링 최적화
  - `FUNC-RETY-002`: 재시도 조건 판별기
  - `FUNC-AUTH-001`: 인증 인터셉터
  - `FUNC-LOG-001`: 보안 로깅 및 메트릭
