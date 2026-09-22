# [ADR-001] courier 풀스택 시스템 아키텍처 및 핵심 기술 스택 결정 레코드

- **작성일자**: 2026-09-22
- **작성자**: 풀스택 아키텍트 (`fullstack-architect`)
- **상태**: APPROVED
- **영향 범위**: HTTP Client Engine, Data Modeling, Response Abstraction, Cascading Configuration, Resilience & Retry, Lifecycle Governance

---

## 1. 배경 및 컨텍스트 (Context & Problem Statement)

현대 마이크로서비스 아키텍처(MSA) 및 데이터 파이프라인 환경에서 백엔드 시스템은 결제 게이트웨이(PG), 알림 발송망, 내부 도메인 서비스, 서드파티 SaaS 등 수많은 외부 HTTP 엔드포인트와 통신합니다. 기획 산출물([`01_PRD.md`](../spec-writer/01_PRD.md), [`02_FUNCTIONAL_SPECIFICATION.md`](../spec-writer/02_FUNCTIONAL_SPECIFICATION.md), [`fsd/HTTP_CLIENT_SPECIFICATION.md`](../spec-writer/fsd/HTTP_CLIENT_SPECIFICATION.md)) 분석 결과, 기존 파이썬 기반 외부 API 연동 방식에는 다음과 같은 중대한 기술적 한계가 존재합니다:

1. **HTTP 전송 계층의 보일러플레이트 중복 및 동기/비동기 파편화**:
   - `requests`와 `aiohttp`로 이원화된 코드베이스로 인해 동기(Flask/Celery) 및 비동기(FastAPI/AsyncIO) 환경 간 코드 재사용이 불가능하며, 엔드포인트마다 세션 생성 및 타임아웃 코드가 수작업으로 중복 양산됨.
2. **비표준화된 응답 처리와 취약한 런타임 예외**:
   - 외부 API마다 제각각인 에러 응답 구조로 인해 `res.json()` 파싱 시 `JSONDecodeError`, 필드 접근 시 `KeyError`가 런타임에 빈발하며, 장황한 `try...except` 블록이 비즈니스 도메인 로직을 침범함.
3. **소켓 누수(Socket Leak) 및 커넥션 풀 라이프사이클 관리 결여**:
   - 요청마다 세션을 임의로 생성/폐기하거나 비동기 루프에서 커넥션을 제대로 닫지 않아 고동시성 부하 시 파일 디스크립터 고갈(`Too many open files`) 및 `CLOSE_WAIT` 소켓 누수 장애 발생.
4. **일시적 네트워크 장애에 대한 회복성(Resilience) 부재**:
   - 일시적인 502/503/504 또는 네트워크 지터 발생 시 체계적인 지수 백오프(Exponential Backoff with Full Jitter)나 `Retry-After` 헤더 준수 메커니즘이 없어 즉각 실패하거나 Thundering Herd 문제를 유발함.
5. **외부 서비스별 설정 관리의 비일관성**:
   - 엔드포인트별 Base URL, 인증 헤더, 타임아웃, 커넥션 풀 크기 등이 코드에 하드코딩되거나 산재되어 중앙 집중식 거버넌스가 불가능함.

이를 해결하기 위해, 본 프로젝트는 **"Zero-Boilerplate, Production-Ready HTTP Client Auto-Configuration"**을 비전으로 수립하고, 선언적이고 파이써닉한 단일 라이브러리 인터페이스를 통해 프로덕션 레벨의 신뢰성을 보장하는 아키텍처 결정을 확정합니다.

---

## 2. 고려된 기술 스택 후보군 (Considered Alternatives)

| 계층 / 핵심 항목 | 후보 1 (선정안) | 후보 2 (대안) | 후보 3 (대안) | 장단점 비교 및 최종 선정 사유 |
| :--- | :--- | :--- | :--- | :--- |
| **HTTP 전송 엔진** | **HTTPX** | `aiohttp` | `requests` | **HTTPX 선정**:<br/>- `Client`(동기)와 `AsyncClient`(비동기)의 완벽한 API 대칭성을 제공하여 단일 라이브러리로 동기/비동기 워크플로우 동시 지원.<br/>- HTTP/2 네이티브 지원 및 `httpx.Limits`를 통한 정밀한 커넥션 풀링 제어 가능.<br/>- `aiohttp`는 동기 API 부재로 범용 라이브러리 적용 불가, `requests`는 비동기 및 HTTP/2 미지원으로 탈락. |
| **설정 및 데이터 모델링** | **Pydantic v2 (`BaseModel`)** | Python `dataclasses` | `attrs` / `marshmallow` | **Pydantic v2 선정**:<br/>- Rust 코어(`pydantic-core`) 기반으로 기존 대비 5~17배 빠른 검증/파싱 성능 보장.<br/>- 환경변수, YAML, JSON 소스로부터의 계층형 설정 로드 및 `model_validate`, `model_dump(mode='json')` 네이티브 지원.<br/>- `dataclasses`는 런타임 검증 및 복잡한 중첩 구조 역직렬화를 위해 서드파티 보조 라이브러리가 필수적이므로 제외. |
| **응답 추상화 패턴** | **Result 패턴 + DTO 역직렬화**<br/>(`ApiResponse[T]`) | 전통적 Python Exception 위주<br/>(`raise_for_status`) | 반환 튜플 패턴<br/>(`tuple[bool, dict, err]`) | **Result 패턴 + 선언적 DTO 변환 선정**:<br/>- Go Resty의 `Result`/`Error` 구조적 분기와 Rust의 `unwrap()`/`ok()` 모나딕 인터페이스를 파이써닉하게 결합.<br/>- Java Feign의 선언적 DTO 매핑 패러다임을 파이썬식 `res.into(Model)`로 재해석하여 한 줄로 타입 세이프 역직렬화 실현.<br/>- 네트워크 에러 발생 시 예외 대신 `status_code=0`과 구조화된 에러를 감싸 반환하여 런타임 크래시를 원천 차단. |
| **회복성 (Resilience)** | **내장 지수 백오프 + Full Jitter & Retry-After 엔진** | `tenacity` 패키지 의존 | `urllib3` 내장 Retry | **내장 Full Jitter 엔진 선정**:<br/>- 외부 무거운 의존성 없이 수학적 Full Jitter 공식($T_{wait} \sim \text{Uniform}(0, T_{exp})$) 및 `Retry-After` 헤더 파싱을 정밀하게 구현.<br/>- Idempotent HTTP 메서드(GET, HEAD, PUT, DELETE) 자동 보호 및 POST 요청 중복 실행 방어(`retry_on_post=False`)를 완벽히 통합.<br/>- `tenacity`는 데코레이터 위주로 HTTP 상태코드 및 동적 대기 시간 조절 시 구조가 복잡해짐. |
| **설정 파서 & 계층 로더** | **PyYAML (`safe_load`) + `json` + ENV Deep Merge** | `Dynaconf` | `python-decouple` | **커스텀 계층 로더 선정**:<br/>- `명시적 kwargs > ENV > YAML > JSON > Defaults` 우선순위의 명확한 캐스케이딩 병합을 최소 의존성으로 구현.<br/>- `yaml.safe_load`를 통한 임의 코드 실행(RCE) 원천 차단.<br/>- `Dynaconf`는 패키지 크기가 크고 불필요한 설정 파일 오버헤드를 유발함. |

---

## 3. 최종 아키텍처 결정 사항 (Decision)

### 3.1 courier 전체 시스템 토폴로지 및 계층 구조

`courier`는 관심사 분리(SoC) 원칙에 따라 5개의 핵심 논리 계층(Layer)으로 구성되며, 각 계층은 단방향 의존성을 준수합니다.

```mermaid
flowchart TD
    subgraph ConfigLayer ["1. 계층형 설정 레이어 (Cascading Configuration Layer)"]
        KWARGS["명시적 인자 (Explicit kwargs)"]
        ENV["환경변수 (HTTP_* / HTTP_SERVICES_*)"]
        YAML["YAML 설정 파일 (courier.yaml)"]
        JSON["JSON 설정 파일 (courier.json)"]
        DEFAULTS["안전한 기본값 (Hardcoded Defaults)"]
        LOADER["CascadingConfigLoader<br/>(우선순위 병합: kwargs > ENV > YAML > JSON > Defaults)"]
        SETTINGS["HttpClientConfig<br/>(Pydantic v2 스키마 검증 및 정규화)"]

        KWARGS --> LOADER
        ENV --> LOADER
        YAML --> LOADER
        JSON --> LOADER
        DEFAULTS --> LOADER
        LOADER --> SETTINGS
    end

    subgraph EngineLayer ["2. 클라이언트 레지스트리 & 전송 엔진 레이어 (Engine & Pool Layer)"]
        REGISTRY["Multi-Service Singleton Registry<br/>(서비스별 HttpClient 캐시 및 라이프사이클 관리)"]
        HTTP_CLIENT["HttpClient (통합 인터페이스)"]
        SYNC_ENGINE["HTTPX Sync Engine<br/>(httpx.Client)"]
        ASYNC_ENGINE["HTTPX Async Engine<br/>(httpx.AsyncClient)"]
        LIMITS["Connection Pool Governance<br/>(httpx.Limits: max_conn, keepalive, expiry)"]
        LIFECYCLE["Lifecycle Governance<br/>(atexit hook, EventLoop guard, close/aclose)"]

        SETTINGS --> REGISTRY
        REGISTRY --> HTTP_CLIENT
        HTTP_CLIENT --> SYNC_ENGINE
        HTTP_CLIENT --> ASYNC_ENGINE
        LIMITS --> SYNC_ENGINE
        LIMITS --> ASYNC_ENGINE
        LIFECYCLE -.-> REGISTRY
    end

    subgraph ResilienceLayer ["3. 회복성 & 재시도 레이어 (Resilience & Retry Layer)"]
        RETRY_ENGINE["RetryEngine"]
        IDEMPOTENCY["Idempotency Checker<br/>(GET/PUT/DELETE vs POST 방어)"]
        BACKOFF["Full Jitter Exponential Backoff<br/>T_exp = min(T_max, factor * 2^k)<br/>T_wait ~ Uniform(0, T_exp)"]
        RETRY_AFTER["Retry-After Header Processor<br/>max(T_wait, Retry-After)"]

        SYNC_ENGINE --> RETRY_ENGINE
        ASYNC_ENGINE --> RETRY_ENGINE
        RETRY_ENGINE --> IDEMPOTENCY
        RETRY_ENGINE --> BACKOFF
        RETRY_ENGINE --> RETRY_AFTER
    end

    subgraph InterceptorLayer ["4. 보안 & 관측성 인터셉터 레이어 (Interceptor Layer)"]
        AUTH["Auth Header Interceptor<br/>(Bearer Token, API-Key 자동 주입)"]
        CORRELATION["Trace & Correlation Interceptor<br/>(X-Request-ID 자동 생성 및 전달)"]
        LOG_MASK["Structured Logging & Masking<br/>(토큰/패스워드 마스킹, duration_ms 측정)"]

        RETRY_ENGINE --> AUTH
        AUTH --> CORRELATION
        CORRELATION --> LOG_MASK
    end

    subgraph ResponseLayer ["5. 통일된 응답 & DTO 변환 레이어 (Response & DTO Layer)"]
        RAW_RESP["httpx.Response / Exception 포획"]
        API_RESP["ApiResponse[T]<br/>(is_success, status_code, data, error, duration_ms)"]
        UNWRAP["Result Pattern (.unwrap() / .ok())"]
        INTO["Declarative DTO Mapping (.into(Type[M]))<br/>(Pydantic model_validate)"]

        LOG_MASK --> RAW_RESP
        RAW_RESP --> API_RESP
        API_RESP --> UNWRAP
        API_RESP --> INTO
    end
```

---

### 3.2 핵심 아키텍처 원칙 및 상세 기술 결정

#### 원칙 1: HTTPX 기반 대칭형 동기/비동기 전송 엔진 및 커넥션 풀 거버넌스
- **동기/비동기 API 대칭성 (API Symmetry)**:
  - 단일 `HttpClient` 인스턴스에서 동기 메서드(`get`, `post`, `put`, `delete`, `patch`)와 비동기 메서드(`async_get`, `async_post`, `async_put`, `async_delete`, `async_patch`)를 완벽히 대칭적으로 노출합니다.
  - 내부적으로 동기 요청은 `httpx.Client`, 비동기 요청은 `httpx.AsyncClient`를 지연 초기화(Lazy Initialization)하여 불필요한 리소스 할당을 방지합니다.
- **커넥션 풀링(Connection Pooling) 상한 규격**:
  - 소켓 누수 및 파일 디스크립터 고갈을 원천 차단하기 위해 엄격한 풀링 정책을 강제합니다:
    ```python
    httpx.Limits(
        max_connections=config.pool_size,               # 기본값: 20, 최대 동시 연결 수
        max_keepalive_connections=config.pool_size // 2, # 유휴 커넥션 상한 (pool_size / 2)
        keepalive_expiry=30.0                           # 유휴 커넥션 유지 시간 (초)
    )
    ```
- **세분화된 타임아웃 거버넌스**:
  - 단일 타임아웃 대신 커넥트 및 리드 타임아웃을 명확히 분리하여 슬로우 로리스(Slowloris) 및 데드락을 방지합니다:
    ```python
    httpx.Timeout(
        timeout=config.timeout,                  # 전체/Read 타임아웃 (기본: 10.0초)
        connect=config.connect_timeout,          # TCP 핸드셰이크 타임아웃 (기본: 3.0초)
        write=config.timeout,                    # Write 타임아웃
        pool=config.connect_timeout              # 풀 획득 대기 타임아웃
    )
    ```
- **HTTP/2 지원**:
  - `http2=True` 설정을 통해 단일 TCP 연결 상에서 멀티플렉싱을 활성화할 수 있는 확장 슬롯을 제공합니다.

---

#### 원칙 2: 5단계 계층형 설정 로더 우선순위 (Cascading Configuration Hierarchy)
- **설정 탐색 및 병합 우선순위**:
  외부 API 연동 시 환경과 런타임에 따른 유연한 오버라이드를 보장하기 위해 다음 5단계 계층 우선순위를 엄격히 준수합니다:
  $$\text{Level 1 (Explicit kwargs)} > \text{Level 2 (ENV)} > \text{Level 3 (YAML)} > \text{Level 4 (JSON)} > \text{Level 5 (Defaults)}$$

  1. **Level 1 (명시적 인자)**: `http.get_client("payment", timeout=5.0, base_url="https://...")`와 같이 런타임 코드에서 직접 전달된 `kwargs` 최우선 적용.
  2. **Level 2 (환경변수 - ENV)**:
     - 서비스별 설정: `HTTP_SERVICES_{SERVICE}_{KEY}` 또는 `HTTP_{SERVICE}_{KEY}` (예: `HTTP_SERVICES_PAYMENT_BASE_URL`, `HTTP_PAYMENT_TIMEOUT`)
     - 전역 공통 설정: `HTTP_BASE_URL`, `HTTP_TIMEOUT`, `HTTP_MAX_RETRIES`
  3. **Level 3 (YAML 파일)**: `courier.yaml`, `courier.yml`, `config.yaml` 파일 내 `services.{service_name}` 및 전역 섹션.
  4. **Level 4 (JSON 파일)**: `courier.json`, `config.json` 파일 내 `services.{service_name}` 섹션.
  5. **Level 5 (안전한 기본값 - Defaults)**: `timeout=10.0s`, `connect_timeout=3.0s`, `max_retries=3`, `backoff_factor=0.5s`, `pool_size=20`.

- **다중 서비스 네임스페이스 격리 및 싱글톤 레지스트리 (Singleton Registry)**:
  - 서비스 식별자(`service_name`)는 대소문자를 구분하지 않는 정규화(`service_name.lower().strip()`)를 거쳐 독립된 설정과 클라이언트로 관리됩니다.
  - 동일한 서비스 식별자로 요청된 클라이언트는 프로세스 내 싱글톤 캐시에서 재사용되어 커넥션 풀을 안전하게 공유합니다.

---

#### 원칙 3: Result 패턴과 선언적 DTO 역직렬화 (Result & DTO Paradigm)
- **통일된 제네릭 응답 모델 (`ApiResponse[T]`)**:
  - 네트워크 단절, DNS 에러, 타임아웃, 4xx/5xx 서버 에러가 발생하더라도 라이브러리는 외부로 날것의 예외를 무분별하게 전파하지 않고 단일 `ApiResponse[T]` 객체로 캡슐화합니다.
  - 응답 모델의 핵심 필드:
    - `status_code: int`: HTTP 상태 코드 ($0$: 네트워크/타임아웃 장애)
    - `is_success: bool`: $200 \le \text{status\_code} < 300$ 인 경우에만 `True`
    - `data: Optional[T]`: 성공 시 JSON 역직렬화 결과 (Dict/List 또는 바인딩된 DTO)
    - `error: Optional[ApiErrorDetail]`: 실패 시 에러 코드, 에러 메시지, 상세 딕셔너리
    - `duration_ms: float`: 요청 시작부터 응답/재시도 종료까지의 총 소요 밀리초
    - `headers: Dict[str, str]`: 대소문자 무관 HTTP 응답 헤더
    - `raw_text: Optional[str]`: 원시 텍스트 본문 (HTML 에러 페이지 디버깅용)
    - `request_url: str`: 실제 호출된 최종 요청 URL
- **Rust 스타일 모나딕 제어 (`unwrap()`) & Go Resty 스타일 구조적 분기**:
  - 개발자는 `if res.is_success:` 구문으로 Go Resty 스타일의 안전한 분기를 처리하거나, `data = res.unwrap()`을 호출하여 Rust 스타일로 성공 데이터를 즉시 취득할 수 있습니다.
  - `unwrap()` 호출 시 실패 응답(`is_success == False`)인 경우 구체적인 실패 맥락을 포함한 `ApiCallError`가 명시적으로 발생합니다.
- **Java Feign의 선언적 DTO 패러다임을 파이써닉하게 수용한 `into()` 메서드**:
  - `res.into(PaymentResponseDto)` 호출 시 Pydantic v2의 `model_validate()`를 통해 타입 검증 및 역직렬화를 단 한 줄로 수행합니다.
  - 스키마 불일치 시 상세 필드 검증 오류 트리를 갖는 `DtoValidationError`를 발생시켜 정적 분석 도구(MyPy, Pyright)와 런타임 안정성을 완벽히 만족합니다.

---

#### 원칙 4: Full Jitter 및 Retry-After 기반 스마트 복원력 (Smart Resilience)
- **Thundering Herd 방지를 위한 Full Jitter 지수 백오프 공식**:
  - 동시 다발적 재시도로 인한 대상 서버 과부하를 방지하기 위해 AWS 권장 Full Jitter 알고리즘을 적용합니다:
    $$T_{exp} = \min(T_{max}, \text{backoff\_factor} \times 2^{k})$$
    $$T_{wait} \sim \text{Uniform}(0, T_{exp})$$
    - $k$: 현재 재시도 차수 ($0 \le k < \text{max\_retries}$)
    - $T_{max}$: 최대 백오프 상한 (기본값: $30.0$초)
    - $\text{backoff\_factor}$: 기본 계수 (기본값: $0.5$초)
- **`Retry-After` 헤더 감지 및 동적 보정**:
  - 대상 서버가 `429 Too Many Requests` 또는 `503 Service Unavailable`과 함께 `Retry-After: <seconds>` 헤더를 반환한 경우, 대기 시간을 즉시 동적으로 보정합니다:
    $$T_{wait} = \max(T_{wait}, \text{parse\_retry\_after}(\text{headers}))$$
  - 단, `Retry-After` 값이 `max_backoff_seconds`를 초과할 경우 즉시 재시도를 포기하고 `ERR_RETRY_AFTER_EXCEEDED` 에러를 반환하여 스레드/코루틴의 무한 블로킹을 방지합니다.
- **멱등성(Idempotency) 기반 재시도 안전망**:
  - 멱등성이 보장되는 메서드(`GET`, `HEAD`, `PUT`, `DELETE`, `OPTIONS`)에 대해서만 자동 재시도를 수행합니다.
  - `POST` 및 `PATCH`와 같은 비멱등(Non-idempotent) 요청은 결제 중복 승인이나 리소스 중복 생성 사고를 방지하기 위해 `retry_on_post=True` 옵션이 명시적으로 활성화되지 않는 한 재시도를 차단합니다.
- **재시도 대상 조건 판별기**:
  - HTTP 상태 코드: $S \in \{429, 502, 503, 504\}$
  - 네트워크 예외: `httpx.ConnectError`, `httpx.ConnectTimeout`, `httpx.ReadTimeout`, `httpx.PoolTimeout`

---

#### 원칙 5: 소켓 누수 방지 및 프로세스 생명주기 거버넌스 (Zero Socket Leak & Lifecycle Governance)
- **Python `atexit` 훅을 통한 소켓 안전 회수**:
  - 애플리케이션 종료(`SIGTERM`, `SIGINT`, 인터프리터 정상 종료) 시점에 레지스트리에 등록된 모든 동기 풀(`client.close()`)과 비동기 풀(`async_client.aclose()`)을 안전하게 닫아 OS 파일 디스크립터 누수를 원천 차단합니다.
- **비동기 이벤트 루프 변경 대응 (EventLoop Lifecycle Guard)**:
  - 비동기 테스트 환경(`pytest-asyncio`)이나 Celery/FastAPI 워커에서 이벤트 루프가 닫히거나 재생성되는 경우(`RuntimeError: Event loop is closed`), 시스템은 이를 자동 감지하여 기존 `AsyncClient`를 폐기하고 활성 루프에 바인딩된 새 클라이언트를 투명하게 재생성합니다.
- **명시적 컨텍스트 매니저 지원**:
  - 단발성 배치나 스크립트 작업을 위해 `with http.get_client(...) as client:` 및 `async with http.get_client(...) as client:` 구문을 완벽 지원합니다.

---

#### 원칙 6: 보안 및 민감 정보 마스킹 거버넌스 (Security & Observability)
- **선언적 인증 인터셉터**:
  - 설정 파일 또는 환경변수에 정의된 `auth.bearer_token` 또는 `auth.api_key`를 감지하여 요청 헤더(`Authorization: Bearer ***`, `X-API-Key: ***`)에 자동 주입합니다.
- **민감 데이터 마스킹 로깅**:
  - 모든 요청/응답 로깅 시 `Authorization`, `X-API-Key`, `Cookie`, `Set-Cookie` 헤더 및 URL 쿼리 파라미터 내 민감 키(`password`, `secret`, `token`, `key`)의 뒤 60% 이상을 `***`로 강제 마스킹하여 로그 수집 시스템으로의 평문 유출을 차단합니다.

---

## 4. 결과 및 트레이드오프 (Consequences)

### 4.1 긍정적 영향 (Positive Impacts)
1. **극적인 개발 생산성 향상**:
   - 외부 API 연동 시 매번 작성하던 40~50줄의 커넥션 풀 설정, 재시도, DTO 매핑 보일러플레이트 코드를 단 2~3줄로 단축 ($\ge 85\%$ 코드량 감소).
2. **런타임 무결성 및 제로 언핸들드 익셉션 (Zero Unhandled Exception)**:
   - 통일된 `ApiResponse[T]`와 Result 패턴 적용으로 예기치 않은 네트워크 중단 및 JSON 디코딩 실패가 런타임 서버 크래시로 번지는 문제를 100% 방어.
3. **프로덕션 레벨의 소켓 누수 0% 달성**:
   - 엄격한 `httpx.Limits` 상한과 `atexit` 라이프사이클 거버넌스를 통해 고동시성 부하 테스트 시 파일 디스크립터 고갈 문제를 원천 차단.
4. **외부 장애 격리 및 서비스 연속성 극대화**:
   - Full Jitter 지수 백오프와 `Retry-After` 헤더 준수를 통해 일시적 네트워크 지터 발생 시 $95\%$ 이상의 자동 복구율을 달성하며 Thundering Herd 방지.

### 4.2 수용된 제약사항 및 완화 방안 (Accepted Trade-offs & Mitigations)
1. **외부 의존성 포함 (`httpx`, `pydantic>=2.0`, `pyyaml`)**:
   - *제약사항*: 표준 라이브러리만을 사용하는 솔루션 대비 패키지 용량 증가 및 종속성 발생.
   - *완화 방안*: 최신 파이썬 생태계에서 사실상 표준으로 자리 잡은 핵심 라이브러리만을 최소한으로 엄선하였으며, Pydantic v2의 Rust 코어 덕분에 순수 파이썬 구현체보다 월등한 성능과 타입 안전성을 획득함.
2. **전통적 Python Exception 모델과의 패러다임 차이**:
   - *제약사항*: Result 패턴(`is_success`, `unwrap()`)이 기존의 `try...except` 위주 코딩 스타일에 익숙한 개발자에게 낯설 수 있음.
   - *완화 방안*: 기존 스타일을 선호하는 개발자를 위해 `unwrap()` 호출 시 친숙한 `ApiCallError` 예외를 발생시키도록 설계하고, 직관적인 문서와 코드 예제를 풍부하게 제공함.
