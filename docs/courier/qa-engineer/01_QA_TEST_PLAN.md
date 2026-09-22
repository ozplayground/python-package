# [courier] 통합 QA 테스트 계획서 (QA Test Plan)

- **작성일자**: 2026-09-22
- **작성자**: 수석 품질 보증 엔지니어 (`qa-engineer`)
- **문서 버전**: v1.0
- **상태**: **Approved**

---

## 1. 테스트 범위 및 환경 (Test Scope & Environment)

### 1.1 테스트 대상
본 테스트 계획서는 파이썬 엔터프라이즈 환경을 위한 고신뢰성 HTTP 클라이언트 라이브러리인 `courier`의 핵심 기능 및 비기능 요구사항을 전수 검증하기 위해 수립되었습니다.
- **기획 및 설계 정합성**:
  - 기획 요구사항 정의서 ([`01_PRD.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/courier/spec-writer/01_PRD.md))
  - 상세 기능 정의서 ([`02_FUNCTIONAL_SPECIFICATION.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/courier/spec-writer/02_FUNCTIONAL_SPECIFICATION.md))
  - 예외 및 엣지 정책서 ([`03_POLICIES_AND_EDGES.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/courier/spec-writer/03_POLICIES_AND_EDGES.md))
  - 아키텍처 결정 레코드 ([`01_ARCHITECTURE_ADR.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/courier/fullstack-architect/01_ARCHITECTURE_ADR.md))
  - 시스템 설계 명세서 ([`01_SYSTEM_DESIGN.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/courier/system-designer/01_SYSTEM_DESIGN.md))
- **대상 핵심 모듈**:
  1. [`courier/response.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/courier/courier/response.py): Result 패턴 컨테이너 (`ApiResponse[T]`), DTO 역직렬화 (`into()`), 민감 헤더 마스킹
  2. [`courier/config.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/courier/courier/config.py): 5단계 계층형 설정 로더 (`ConfigLoader`), `ClientConfig`, `RetryConfig`
  3. [`courier/retry.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/courier/courier/retry.py): Full Jitter 지수 백오프, RFC 7231 `Retry-After` 헤더 파서, SSL Fail-Fast 재시도 엔진
  4. [`courier/client.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/courier/courier/client.py): 동기/비동기 이중 엔진 (`HttpClient`), 전역 싱글톤 프록시 (`http`), 커넥션 풀링 및 1MB Truncation 안전망
  5. [`courier/decorators.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/courier/courier/decorators.py): 선언적 API 인터페이스 (`@courier`, `@get`, `@post`, `@put`, `@delete`, `@patch`)

### 1.2 테스트 환경
- **런타임 및 OS 플랫폼**:
  - Python: `3.11` (호환성 보장: `3.10 ~ 3.13`)
  - 운영체제: macOS (darwin arm64) 및 Linux (Ubuntu 22.04 LTS x86_64)
- **핵심 라이브러리 및 프레임워크**:
  - HTTP 엔진: `httpx >= 0.28.1`
  - 데이터 모델링 & 검증: `pydantic >= 2.10.6`
  - 설정 파싱: `pyyaml >= 6.0.2`
- **테스트 & 품질 보증 툴체인**:
  - 테스트 러너: `pytest >= 8.3.4`
  - 비동기 테스트 플러그인: `pytest-asyncio >= 1.4.0` (auto 모드)
  - 커버리지 분석: `pytest-cov >= 7.1.0` (목표 커버리지 >= 95%)
  - HTTP 인메모리 모킹: `respx >= 0.23.1` (외부 네트워크 I/O 격리 보장)
- **동시성 및 리소스 환경**:
  - 멀티스레드: `concurrent.futures.ThreadPoolExecutor` (50 동시 스레드)
  - 멀티코루틴: `asyncio.gather` (100 동시 코루틴)
  - 소켓 누수 방지: `atexit.register` 및 명시적 리소스 수거 확인

---

## 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 케이스 ID | 테스트 구분 | 검증 시나리오 | 사전 조건 및 입력 데이터 | 기대 결과 (Pass Criteria) |
| :--- | :---: | :--- | :--- | :--- |
| **`TC-RESP-001`** | **Result 패턴 & DTO** | **`ApiResponse` Result 패턴 (`unwrap`, `into`, `is_success`, `safe_headers`) 동작 검증** | 200 OK JSON 응답 수신, 대상 Pydantic 모델 지정 (`SampleUserDto`) | - `is_success=True`<br>- `unwrap()` 호출 시 원시 데이터 딕셔너리 반환<br>- `into(DTO)` 호출 시 Pydantic DTO 인스턴스로 자동 파싱<br>- Authorization 헤더 등 민감정보 마스킹(`***`) 확인 |
| `TC-RESP-002` | Result 예외 처리 | 실패 응답(404, 500) 수신 시 `unwrap()` 및 `unwrap_or()` 동작 검증 | 404 Not Found 및 500 Internal Error 모의 응답 | - `unwrap()` 호출 시 `ApiCallError` 예외 발생 (내부에 원인 `ApiError` 포함)<br>- `unwrap_or(default)` 호출 시 지정한 기본값 반환 |
| `TC-RESP-003` | DTO 스키마 불일치 | 응답 본문 구조와 Pydantic 모델 불일치 시 `into()` 검증 | 필수 필드가 누락된 JSON 본문 반환 | `DtoValidationError` 예외 발생 및 검증 오류 상세 내역과 본문 요약 포함 확인 |
| `TC-RESP-004` | 204 No Content | 응답 본문이 비어 있는 204 No Content 응답 처리 | HTTP 204 No Content 응답 | `is_success=True`, `data=None`, `unwrap() is None` 정상 처리 |
| **`TC-CONF-001`** | **계층형 설정** | **5단계 계층 우선순위 (`kwargs > ENV > YAML > JSON > Defaults`) 및 멀티 서비스 클라이언트 캐싱** | 환경 변수(`HTTP_CLIENT_...`), 임시 `http_clients.yaml`, `http_clients.json` 및 `kwargs` 설정 | - 상위 계층의 설정값이 하위 설정을 정확히 덮어씀 (kwargs > ENV > YAML > JSON > Defaults)<br>- 동일 서비스명 호출 시 캐시된 싱글톤 인스턴스 반환<br>- 오버라이드 매개변수 제공 시 갱신된 클라이언트 생성 |
| `TC-CONF-002` | 설정 유효성 검증 | 잘못된 `base_url` 스키마 및 음수 타임아웃 주입 시 검증 | `ftp://...`, `not-a-valid-url`, `timeout=-1.0` 주입 | `ConfigurationValidationError` 및 Pydantic `ValidationError` 즉시 발생 |
| `TC-CONF-003` | HTTPX 객체 변환 | `ClientConfig`를 `httpx.Limits` 및 `httpx.Timeout`으로 변환 | 커스텀 풀 크기(50), 타임아웃(12s) 설정 | `to_httpx_limits()` 및 `to_httpx_timeout()`이 정확한 HTTPX 구조체 생성 |
| **`TC-RETY-001`** | **회복성 & 재시도** | **AWS Full Jitter 지수 백오프 공식 및 `Retry-After` 헤더 파싱/클램핑 검증** | 503 Service Unavailable 및 429 Too Many Requests (헤더: `Retry-After: 5` 또는 RFC 7231 HTTP-Date) | - 재시도 대기 시간: $0 \le T_{wait} \le \min(T_{max}, \text{backoff} \times 2^k)$ 범위 내 균등 난수 분포<br>- `Retry-After` 초 단위 및 HTTP-Date 정확히 파싱되어 대기 시간에 반영<br>- `Retry-After > 30s` 초과 시 블로킹 방지를 위해 즉시 재시도 포기(Fail-Fast) |
| `TC-RETY-002` | 재시도 소진 & 멱등성 | 504 Gateway Timeout 지속 발생 시 최대 재시도 소진 및 비멱등(POST) 기본 정책 | `max_retries=2`, 504 응답 지속, POST 요청 시뮬레이션 | - 최대 3회(초기 1 + 재시도 2) 시도 후 마지막 응답 반환<br>- `retry_on_post=False` 기본값 상태에서 POST는 재시도 없이 1회 만에 즉시 반환 |
| `TC-RETY-003` | SSL 에러 재시도 배제 | `ssl.SSLError` 및 래핑된 인증서 오류 발생 시 재시도 중단 | `ssl.SSLError("Certificate verification failed")` 발생 | 재시도 루프 즉시 중단(1회 호출 후 종료), 불필요한 백오프 대기 없음 |
| **`TC-CONC-001`** | **동시성 & 소켓 제로 누수** | **50 스레드 / 100 코루틴 고동시성 스트레스 및 소켓 리소스 완전 해제 검증** | `ThreadPoolExecutor` 50 동시 요청, `asyncio.gather` 100 동시 요청, 20 동시 503 트래픽 폭풍 | - 50개 스레드 및 100개 코루틴 전수 200 OK 수신 및 데이터 정합성 유지<br>- 커넥션 풀 경합 시 소켓 교착(Deadlock) 없음<br>- `client.close()`, `client.aclose()`, `http.close_all()` 호출 시 열린 소켓 0개 보장 |
| **`TC-DEC-001`** | **선언적 데코레이터** | **선언적 클라이언트 인터페이스 (`@courier`, `@get`, `@post`, `@put`, `@delete`) 기능 검증** | 클래스 레벨 `@courier`, 메서드 레벨 `@get("/users/{user_id}")`, `@post`, Pydantic Body | - 경로 파라미터(`{user_id}`) 자동 포맷팅 및 URL 치환<br>- Pydantic 요청 객체 자동 JSON 직렬화<br>- 동기 및 비동기(`async def`) 메서드 투명 지원<br>- 필수 경로 파라미터 누락 시 `ValueError` 발생 |
| `TC-ENG-001` | 엔진 안전망 | 1MB 초과 대용량 페이로드 Truncation 및 비동기 이벤트 루프 재생성 안전성 | 1MB+500B 응답 페이로드 수신, 비동기 호출 중 이벤트 루프 강제 닫힘 및 교체 | - 1MB 초과 바이트 수신 시 메모리 절삭 및 경고 문구 추가 (`[TRUNCATED: ...]`)<br>- 교체되거나 닫힌 이벤트 루프 감지 시 새 `AsyncClient`로 재바인딩되어 크래시 방지 |

---

## 3. 합격 기준 (Pass Criteria)

1. **테스트 통과율 100%**: 전체 72개 단위 및 통합 테스트 케이스 무결점 통과 (0 Failures, 0 Errors).
2. **코드 커버리지 95% 이상**: `courier` 패키지 전체 라인 커버리지 95% 이상 달성.
3. **결함 허용 기준**: Blocker 0건, Critical 0건, Minor 0건 (모든 결함 수정 완료 후 출시).
4. **보안 및 리소스 기준**:
   - YAML 임의 코드 실행(RCE) 방지 (`yaml.safe_load`).
   - 대용량 응답(>1MB) 수신 시 프로세스 OOM 방지 절삭 처리.
   - 프로세스 종료 시 잔여 소켓 누수 0개 (`atexit` 등록 확인).
