# [courier] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-23
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.1 (Humanizer 지침 반영 개정판)
- **상태**: Approved

---

## 1. 기능 계층 구조도 (Feature Hierarchy Tree)

Courier 패키지의 전체 기능 구조는 외부 HTTP API 통신 시 마주하는 5개 엔지니어링 영역으로 구분됩니다.

```
[1Depth: courier]
  ├── [2Depth: 응답 추상화 (Response & Serialization)]
  │     ├── [3Depth: 통일된 제네릭 응답 객체 ApiResponse[T]] (FUNC-RESP-001)
  │     └── [3Depth: Pydantic v2 DTO 역직렬화 및 Result 패턴 unwrap] (FUNC-RESP-002)
  ├── [2Depth: 설정 관리 (Cascading Configuration)]
  │     ├── [3Depth: 다중 서비스 계층형 설정 로더 및 자동 병합] (FUNC-CONF-001)
  │     └── [3Depth: Pydantic 기반 클라이언트 설정 유효성 검증] (FUNC-CONF-002)
  ├── [2Depth: 커넥션 및 코어 엔진 (Connection & Engine)]
  │     ├── [3Depth: HTTPX 기반 동기/비동기 듀얼 코어 클라이언트] (FUNC-ENG-001)
  │     └── [3Depth: 싱글톤 커넥션 풀 유지 및 atexit 프로세스 정리] (FUNC-ENG-002)
  ├── [2Depth: 장애 회복성 (Resilience & Retry)]
  │     ├── [3Depth: Full Jitter 지수 백오프 스마트 재시도 엔진] (FUNC-RETY-001)
  │     └── [3Depth: 429/5xx 상태코드 및 네트워크 타임아웃 판별기] (FUNC-RETY-002)
  └── [2Depth: 보안 및 관측성 (Security & Observability)]
        ├── [3Depth: Bearer / API Key 인증 헤더 자동 주입 인터셉터] (FUNC-AUTH-001)
        └── [3Depth: 민감정보 마스킹 구조화 로깅 및 레이턴시 추적] (FUNC-LOG-001)
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

각 기능의 세부 구현 요건, 8대 데이터 항목 명세, 비즈니스 규칙 및 예외 처리 가이드는 [`fsd/HTTP_CLIENT_SPECIFICATION.md`](./fsd/HTTP_CLIENT_SPECIFICATION.md)에 상세 기술되어 있습니다.

| 기능 ID | 1Depth (영역) | 2Depth (모듈) | 3Depth (단위기능명) | 우선순위 | 대응 요구사항 ID | 상세 명세 링크 |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `FUNC-RESP-001` | 응답 추상화 | 응답 래퍼 | 통일된 제네릭 응답 모델 `ApiResponse[T]` | Must | `REQ-RESP-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-001) |
| `FUNC-RESP-002` | 응답 추상화 | DTO 변환 | Result 패턴 `unwrap()` 및 Pydantic `into()` 역직렬화 | Must | `REQ-DTO-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-resp-002) |
| `FUNC-CONF-001` | 설정 관리 | 설정 로더 | 다중 서비스 계층형 설정 로더 (ENV > YAML > JSON > Defaults) | Must | `REQ-CONF-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-001) |
| `FUNC-CONF-002` | 설정 관리 | 스키마 검증 | Pydantic 기반 HTTP 클라이언트 설정 유효성 검증 | Must | `REQ-CONF-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-conf-002) |
| `FUNC-ENG-001` | 코어 엔진 | 클라이언트 | HTTPX 코어 클라이언트 (동기/비동기 동시 지원 인터페이스) | Must | `REQ-ENG-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-001) |
| `FUNC-ENG-002` | 코어 엔진 | 커넥션 풀 | 고동시성 무누수 커넥션 풀링 최적화 및 `atexit` 안전 해제 | Must | `REQ-ENG-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-eng-002) |
| `FUNC-RETY-001` | 회복성 | 재시도 엔진 | Full Jitter 지수 백오프 스마트 재시도 | Must | `REQ-RETY-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-001) |
| `FUNC-RETY-002` | 회복성 | 재시도 판별 | 429/5xx 상태코드 및 네트워크 타임아웃 판별기 | Must | `REQ-RETY-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-002`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-rety-002) |
| `FUNC-AUTH-001` | 보안/인증 | 인터셉터 | Bearer Token 및 API Key 인증 헤더 자동 주입 인터셉터 | Should | `REQ-AUTH-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-auth-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-auth-001) |
| `FUNC-LOG-001` | 관측성 | 로깅/메트릭 | 민감정보 마스킹 구조화 로깅 및 레이턴시 추적 | Should | `REQ-LOG-001` | [`fsd/HTTP_CLIENT_SPECIFICATION.md#func-log-001`](./fsd/HTTP_CLIENT_SPECIFICATION.md#func-log-001) |

---

## 3. 상세 명세 문서 맵 (Modular FSD Map)

- [HTTP 클라이언트 및 통일 응답 상세기능정의서 (Modular FSD)](./fsd/HTTP_CLIENT_SPECIFICATION.md)
  - 핵심 단위기능 4건(`FUNC-RESP-001`, `FUNC-CONF-001`, `FUNC-ENG-001`, `FUNC-RETY-001`)에 대해 7대 상세 명세 및 8대 데이터 항목 표를 완비하여 기술합니다.
