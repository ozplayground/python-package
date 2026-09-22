# [courier] 비즈니스 정책 및 전역 예외 처리 명세서 (Policy & Edge Cases)

- **작성일자**: 2026-09-22
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. 핵심 HTTP 클라이언트 및 요청 생명주기 상태 전이 머신 (State Machine Policies)

`courier`가 관리하는 클라이언트 초기화, HTTP 요청 생명주기, 그리고 회복성(재시도) 엔진의 상태 전이도입니다.

```mermaid
stateDiagram-v2
    [*] --> UNINITIALIZED: 패키지 로드
    UNINITIALIZED --> CONFIG_RESOLVED: 계층형 설정 로드 및 병합 (ENV > YAML > JSON > Defaults)
    CONFIG_RESOLVED --> CLIENT_READY: HttpClient 싱글톤 인스턴스 생성 및 풀 준비

    state CLIENT_READY {
        [*] --> IDLE: 유휴 상태 (Idle Connection Pool)
        IDLE --> REQUEST_PREPARING: get/post/async_get 호출 인입
        REQUEST_PREPARING --> IN_FLIGHT: 인터셉터 헤더 주입 및 소켓 전송
        IN_FLIGHT --> RESPONSE_RECEIVED: 원시 응답 수신 (2xx, 3xx, 4xx, 5xx)
        IN_FLIGHT --> NETWORK_FAILED: 소켓 에러 또는 타임아웃 발생

        RESPONSE_RECEIVED --> EVALUATING_RETRY: 상태코드 검사 (429, 502, 503, 504 등)
        NETWORK_FAILED --> EVALUATING_RETRY: 재시도 대상 예외 여부 검사

        EVALUATING_RETRY --> BACKOFF_WAITING: 재시도 조건 충족 (k < max_retries)
        BACKOFF_WAITING --> IN_FLIGHT: 지수 백오프 + Jitter 대기 완료 후 재전송

        EVALUATING_RETRY --> FINAL_SUCCESS: 2xx 수신 및 파싱 성공
        EVALUATING_RETRY --> FINAL_FAILURE: 재시도 횟수 소진 또는 비재시도 에러 (4xx 등)

        FINAL_SUCCESS --> IDLE: ApiResponse[T] 반환 및 소켓 커넥션 풀 반환
        FINAL_FAILURE --> IDLE: ApiResponse[T] (에러 상세 포함) 반환 및 소켓 반환
    }

    CLIENT_READY --> CLOSED: atexit / client.close() / async_client.aclose() 호출
    CLOSED --> [*]
```

### 1.1 상태 전이 매트릭스 및 규칙

| 현재 상태 | 대상 상태 | 전이 트리거 이벤트 | 필수 사전 조건 | 실행 주체 및 사후 동작 |
| :--- | :--- | :--- | :--- | :--- |
| `UNINITIALIZED` | `CONFIG_RESOLVED` | `http.get_client(service)` 최초 호출 | 설정 파일(YAML/JSON), ENV, 또는 기본값 존재 | 계층 우선순위(`kwargs > ENV > YAML > JSON > Defaults`) 병합 및 `HttpClientConfig` Pydantic 검증 |
| `CONFIG_RESOLVED` | `CLIENT_READY` | 클라이언트 팩토리 초기화 | 유효한 `HttpClientConfig` 보유 | `httpx.Limits` 및 타임아웃을 적용한 내부 엔진 인스턴스화, 싱글톤 레지스트리 등록 |
| `IDLE` | `REQUEST_PREPARING` | API 호출 메서드 실행 (`get`, `async_get` 등) | 클라이언트가 활성 상태(`not is_closed`) | 인터셉터 체인 실행, Correlation-ID (`X-Request-ID`) 생성, 시작 시각 $t_{start}$ 기록 |
| `REQUEST_PREPARING` | `IN_FLIGHT` | 소켓 요청 발송 | 파라미터 및 헤더 정합성 검증 완료 | 가용 커넥션 체크아웃 후 네트워크 I/O 실행 |
| `IN_FLIGHT` | `RESPONSE_RECEIVED`| 대상 서버로부터 바이트 스트림 수신 완료 | HTTP 헤더 및 상태코드 수신 완료 | 소요 시간 $\Delta t$ 측정 및 본문 파싱 준비 |
| `IN_FLIGHT` | `NETWORK_FAILED` | DNS 오류, 소켓 연결 실패, 타임아웃 발생 | 네트워크 I/O 중단 | `httpx.TransportError` 포착 및 에러 컨텍스트 기록 |
| `RESPONSE_RECEIVED` / `NETWORK_FAILED` | `EVALUATING_RETRY` | 결과 평가 단계 진입 | 응답 객체 또는 에러 객체 확보 | 상태코드 $\in \{429, 502, 503, 504\}$ 또는 타임아웃 여부 및 멱등성 검사 |
| `EVALUATING_RETRY` | `BACKOFF_WAITING` | 재시도 결정 | $k < K_{max}$ 이고 멱등 메서드이거나 `retry_on_post=True` | Full Jitter 백오프 대기 시간 $T_{wait}$ 계산 |
| `BACKOFF_WAITING` | `IN_FLIGHT` | 대기 완료 ($T_{wait}$ 경과) | 동기 `sleep` 또는 비동기 `asyncio.sleep` 완료 | 재시도 카운트 $k \leftarrow k + 1$ 증가 후 재요청 발송 |
| `EVALUATING_RETRY` | `FINAL_SUCCESS` | 성공 응답 확인 | 상태코드 $200 \le S < 300$ | `is_success=True`, `data`에 JSON 파싱 결과 바인딩 |
| `EVALUATING_RETRY` | `FINAL_FAILURE` | 재시도 소진 또는 비재시도 에러 | $k \ge K_{max}$ 또는 비재시도 상태코드(400, 401, 403, 404 등) | `is_success=False`, `error`에 `ApiErrorDetail` 바인딩 |
| `FINAL_SUCCESS`/`FINAL_FAILURE` | `IDLE` | `ApiResponse[T]` 반환 | 소켓 스트림 닫힘 및 풀 반환 | 커넥션 유지(Keep-Alive) 또는 소켓 정상 종료 |
| `CLIENT_READY` | `CLOSED` | 프로세스 종료 또는 명시적 `close()` | `atexit` 시그널 또는 사용자 종료 요청 | 모든 활성 커넥션 풀 강제 종료 및 OS 소켓 해제 |

---

## 2. 공통 비즈니스 제약 및 유효성 검증 정책 (Global Business Policies)

### 2.1 계층형 설정 우선순위 정책 (Cascading Configuration Policy)
- **우선순위 순서**:
  1. **명시적 인자 (`kwargs`)**: `http.get_client("svc", timeout=5.0)`와 같이 코드 레벨에서 직접 주입한 값이 최우선.
  2. **환경변수 (`ENV`)**: `HTTP_CLIENT_{SERVICE}_{KEY}` 형식 (예: `HTTP_CLIENT_PAYMENT_BASE_URL`). 대소문자는 무시되고 언더바(`_`)로 구분.
  3. **YAML 설정 파일 (`.yaml` / `.yml`)**: `courier.yaml`, `http_clients.yaml`, `config.yaml`의 `{service_name}` 블록.
  4. **JSON 설정 파일 (`.json`)**: `courier.json`, `http_clients.json`, `config.json`의 `{service_name}` 블록.
  5. **기본값 (Hardcoded Defaults)**: 프로덕션 표준 안전 기본값.
- **병합 규칙 (Deep Merge)**: 상위 계층의 설정이 하위 계층의 동일 키를 완전히 대체(Override)하며, 정의되지 않은 키만 하위 계층에서 상속받습니다.

### 2.2 전역 타임아웃 정책 (Timeout Granularity Policy)
- 타임아웃은 단일 값이 아닌 4개 세부 단계로 분리 관리하여 Slowloris 공격 및 네트워크 블랙홀을 방어합니다:
  - **`connect_timeout` (기본값: 3.0초)**: 대상 서버와의 TCP 핸드셰이크 및 TLS 네고시에이션 최대 대기 시간. 3초 초과 시 즉시 차단.
  - **`read_timeout` (기본값: 10.0초)**: 연결 수립 후 대상 서버로부터 응답 바이트를 수신하기까지의 최대 대기 시간.
  - **`write_timeout` (기본값: 10.0초)**: 요청 바이트를 네트워크 버퍼에 쓰기까지의 최대 대기 시간.
  - **`pool_timeout` (기본값: 5.0초)**: 커넥션 풀의 모든 소켓이 사용 중일 때 가용 소켓이 반환되기를 대기하는 최대 시간. 초과 시 `ERR_ENG_POOL_EXHAUSTED` 발생.

### 2.3 스마트 재시도 및 지수 백오프 공식 (Exponential Backoff with Full Jitter)
- **기본 계산식**:
  $$T_{exp} = \min(T_{max}, \text{backoff\_factor} \times 2^{attempt})$$
  $$T_{wait} \sim \text{Uniform}(0, T_{exp})$$
  - $\text{backoff\_factor}$: 기본값 `0.5`초
  - $T_{max}$: 최대 대기 시간 상한선, 기본값 `30.0`초
  - $attempt$: 현재 재시도 차수 ($0, 1, 2, \dots$)
- **`Retry-After` 헤더 연동 규칙**:
  - 외부 서버가 `429 Too Many Requests` 또는 `503 Service Unavailable`과 함께 `Retry-After: <value>`를 반환한 경우:
    - 정수 형태(초 단위): $T_{wait} = \max(T_{wait}, \text{int}(Retry-After))$
    - HTTP-Date 형태: 대상 시각과 현재 UTC 시각의 차이를 계산하여 초 단위로 변환 후 적용.
    - 만약 파싱된 대기 시간이 `max_backoff_seconds`(30s)를 초과하면 추가 대기를 하지 않고 즉시 재시도를 포기하여 시스템 블로킹을 방지합니다.
- **멱등성(Idempotency) 보장 원칙**:
  - `GET`, `HEAD`, `PUT`, `DELETE`, `OPTIONS`는 멱등 요청이므로 자동 재시도를 수행합니다.
  - `POST`, `PATCH`는 비멱등 요청이므로 중복 결제/중복 리소스 생성 사고를 방지하기 위해 `retry_on_post=True`가 명시적으로 활성화되지 않은 경우 절대 재시도하지 않습니다.

### 2.4 커넥션 풀링 및 소켓 수명 관리 정책 (Connection Pool Management)
- **`max_connections` (기본값: 20)**: 호스트당 유지 가능한 최대 동시 소켓 수.
- **`max_keepalive_connections` (기본값: 10)**: 재사용을 위해 유휴 상태로 유지하는 Keep-Alive 소켓 수.
- **`keepalive_expiry` (기본값: 30.0초)**: 유휴 커넥션 자동 정리 주기. 방화벽 유휴 세션 단절로 인한 좀비 소켓 생성 방지.
- **전역 싱글톤 재사용**: 동일 서비스(`service_name`)는 동일한 클라이언트 인스턴스를 공유하며 매 요청마다 클라이언트를 인스턴스화하지 않습니다.
- **프로세스 종료 훅 (`atexit`)**: Python 인터프리터 종료 시 등록된 모든 활성 클라이언트를 순회하며 커넥션 풀을 안전하게 닫아 OS 파일 디스크립터 누수를 원천 차단합니다.

### 2.5 보안 및 민감 정보 마스킹 정책 (Security & Redaction Policy)
- **헤더 마스킹**: 로깅 시 `Authorization`, `Proxy-Authorization`, `X-API-Key`, `Cookie`, `Set-Cookie` 헤더 값은 앞 4글자만 노출하고 나머지는 `***`로 마스킹합니다 (예: `Bearer eyJh***`).
- **쿼리 및 페이로드 마스킹**: 키 명칭에 `password`, `secret`, `token`, `key`, `credential`이 포함된 경우 해당 값은 `[REDACTED]`로 치환하여 로그에 기록합니다.

### 2.6 시간 및 타임존 정책 (Timezone & Precision Policy)
- 모든 요청 기록 타임스탬프는 **UTC 기준 ISO 8601** 형식(`YYYY-MM-DDTHH:mm:ss.sssZ`)으로 기록합니다.
- 소요 시간(`duration_ms`)은 고정밀도 타이머(`time.perf_counter`)를 사용하여 밀리초 단위 소수점 둘째자리까지 정확히 측정합니다.

---

## 3. 전역 엣지 케이스 및 장애 복구 가이드 (Global Edge Cases & Recovery)

| 장애 / 예외 유형 | 감지 방식 | 시스템 처리 방식 및 가이드 |
| :--- | :--- | :--- |
| **DNS Lookup 실패 (Host Unreachable)** | `httpx.ConnectError` 포착 (호스트명 해석 불가) | 즉시 재시도 대상(총 3회)으로 분류하여 지수 백오프로 재시도하되, 최종 실패 시 `status_code=0`, `error.code="ERR_ENG_CONNECT_FAILED"`로 통일된 `ApiResponse` 반환 |
| **SSL/TLS Handshake 실패** | `httpx.ConnectError` 중 `ssl.SSLError` 감지 | 인증서 만료 또는 도메인 불일치 등 보안 예외는 재시도해도 성공 불가능하므로 **즉시 재시도를 중단**하고 보안 에러 코드 반환 |
| **Slowloris / Read Timeout 지연** | `read_timeout`(10.0s) 초과 | 소켓 버퍼를 즉시 강제 리셋(RST)하고 해당 커넥션을 풀에서 폐기한 후, 멱등 요청인 경우 새 소켓으로 1회 재시도 |
| **HTTP 429 Too Many Requests (Rate Limit)** | 응답 상태코드 429 감지 | `Retry-After` 헤더 유무 확인 후, 지정된 시간(최대 30초 한도 내)만큼 대기한 뒤 재전송. Thundering Herd 방지를 위해 지터 추가 |
| **대용량 비정형 Response Body 메모리 보호** | 응답 본문 크기 1MB 초과 시 | 무제한 메모리 적재 방지를 위해 `raw_text`는 앞선 1MB(1,048,576 bytes)까지만 버퍼링하고 `[TRUNCATED: Response body exceeded 1MB]` 접미사 추가 |
| **비동기 이벤트 루프 종료 후 호출** | `RuntimeError: Event loop is closed` 감지 | 이전 루프에 바인딩된 `httpx.AsyncClient`를 안전하게 파기하고, 현재 실행 중인 활성 루프(`asyncio.get_running_loop()`)에 맞추어 새 비동기 클라이언트를 투명하게 재생성 |
| **Non-JSON 본문 수신 시 DTO 변환 시도** | `into(Model)` 호출 시 `data`가 `None` 또는 `str` | 즉시 `DtoValidationError`를 발생시키며 원시 본문(`raw_text`) 앞 200자를 에러 메시지에 포함하여 디버깅 편의 제공 |
| **Thundering Herd 트래픽 폭풍 방지** | 다수 워커의 동시 장애 재시도 인입 | 모든 재시도 대기 시간에 균등 분포(Full Jitter, `random.uniform(0, T_exp)`)를 의무화하여 재시도 요청이 시간축 전체에 고르게 분산되도록 보장 |
