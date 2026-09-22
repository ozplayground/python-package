# [courier] HTTP 클라이언트 및 응답 자동 구성 상세기능정의서 (Modular FSD)

- **도메인**: HTTP 클라이언트 자동 구성 및 통일된 응답 (HTTP Client Auto-Configuration & Unified Response)
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 단위 기능 상세 명세 (단위기능별 7대 상세 명세 완비)

---

### [FUNC-RESP-001] 통일된 제네릭 응답 모델 `ApiResponse[T]` (Unified Generic ApiResponse Wrapper)

#### 1. 기본 정보
- **기능명**: 통일된 제네릭 응답 모델 `ApiResponse[T]` 및 결과 제어
- **기능 ID**: `FUNC-RESP-001`
- **대응 요구사항 ID**: `REQ-RESP-001`, `REQ-DTO-001`
- **대상 모듈 코드**: `MOD-RESP-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 라이브러리 사용자 (백엔드 엔지니어, API 클라이언트 호출자)

#### 2. 사전 조건 (Pre-conditions)
1. 클라이언트(`HttpClient`)를 통해 동기 또는 비동기 HTTP 요청이 실행된 상태.
2. 원시 HTTP 응답(`httpx.Response`)이 수신되었거나, 네트워크 단절/타임아웃 등 네트워크 계층 예외가 포착된 상태.
3. 요청 시작 시각($t_{start}$)과 종료 시각($t_{end}$)이 밀리초 단위로 기록된 상태.

#### 3. 사용자 인터랙션 및 시스템 동작 흐름과 플로우차트 (Step-by-Step Flow & Flowchart)
1. 호출자가 `client.get(...)` 또는 `await client.async_get(...)`을 호출한다.
2. 시스템은 네트워크 요청을 전송하고 총 소요 시간 $\Delta t = (t_{end} - t_{start}) \times 1000$ (ms)를 측정한다.
3. 응답 수신 시 HTTP 상태 코드 $S$를 판별한다:
   - **$200 \le S < 300$**: `is_success = True`로 설정하고 본문을 JSON으로 파싱하여 `data`에 할당한다. 만약 본문이 비어있거나 JSON 파싱 불가 시 원시 텍스트 또는 `None`을 할당하고 `error = None`으로 초기화한다.
   - **$S \ge 300$**: `is_success = False`로 설정하고 `error` 필드에 `ApiErrorDetail(code=..., message=..., details=...)` 객체를 생성하여 바인딩한다.
4. 네트워크 단절 또는 타임아웃으로 응답 객체 자체가 없는 경우, 예외를 삼키지 않고 `status_code = 0`, `is_success = False`, `data = None`, `error = ApiErrorDetail(code='NETWORK_ERROR' or 'TIMEOUT', message=str(exc))`를 갖는 `ApiResponse`를 생성한다.
5. 호출자는 `res.is_success` 분기를 검사하거나, Rust 스타일의 `res.unwrap()`을 호출하여 성공 시 `data`를 즉시 취득하고 실패 시 상세 `ApiCallError` 예외를 발생시킨다.
6. 호출자가 Pydantic 모델 클래스를 전달하여 `res.into(UserModel)`을 호출하면, `data` 딕셔너리를 해당 Pydantic 모델 인스턴스로 자동 역직렬화하여 타입 추론된 모델을 반환한다.

```mermaid
flowchart TD
    A[HTTP 요청 실행] --> B[소요 시간 duration_ms 측정]
    B --> C{HTTP 응답 수신 성공?}
    C -- 예외 발생 (네트워크/타임아웃) --> D[status_code=0, is_success=False 설정]
    D --> E[ApiErrorDetail에 예외 메시지 바인딩]
    C -- 응답 수신됨 --> F{상태 코드 200 <= status < 300?}
    F -- 성공 (2xx) --> G[is_success=True, error=None 설정]
    G --> H{본문 JSON 파싱 시도}
    H -- JSON 파싱 성공 --> I[data에 Dict/List 할당]
    H -- 파싱 실패 / 빈 본문 --> J[raw_text 보존 및 data=None 할당]
    F -- 실패 (3xx/4xx/5xx) --> K[is_success=False 설정]
    K --> L[에러 본문 파싱하여 ApiErrorDetail 생성]
    E --> M[최종 ApiResponse[T] 인스턴스 반환]
    I --> M
    J --> M
    L --> M
    M --> N{호출자 unwrap() 또는 into() 호출}
    N -- unwrap() & is_success=True --> O[data 반환]
    N -- unwrap() & is_success=False --> P[ApiCallError 예외 발생]
    N -- into(PydanticModel) --> Q[Pydantic model_validate(data) 반환]
```

#### 4. 화면 표시 및 입력 데이터 항목 명세 (UI Data Elements - 8대 표준 컬럼)

| 항목명 | 화면 표시/입력 구분 | UI 컴포넌트 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출/수정 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `status_code` | 응답 속성 | Model Property | 필수 | Integer (0 ~ 599) | `0` | 유효 HTTP 상태 코드 범위 (0: 네트워크 실패) | 상시 |
| `is_success` | 응답 속성 | Model Property | 필수 | Boolean | `False` | $200 \le \text{status\_code} < 300$ 시 True | 상시 |
| `data` | 응답 속성 | Model Property | 선택 | Generic `Optional[T]` | `None` | 성공 시 JSON 역직렬화 객체 또는 None | `is_success=True` 시 데이터 바인딩 |
| `error` | 응답 속성 | Model Property | 선택 | `Optional[ApiErrorDetail]` | `None` | 실패 시 에러 코드, 메시지, 상세 딕셔너리 | `is_success=False` 시 필수 포함 |
| `duration_ms` | 응답 속성 | Model Property | 필수 | Float (밀리초) | `0.0` | $\ge 0.0$ (소수점 둘째자리 반올림) | 상시 |
| `headers` | 응답 속성 | Model Property | 필수 | `Dict[str, str]` (Case-insensitive) | `{}` | Key-Value 형태의 헤더 맵 | 상시 |
| `raw_text` | 응답 속성 | Model Property | 선택 | `Optional[str]` | `None` | 원시 텍스트 본문 (최대 1MB 안전 버퍼) | 디버깅 및 비JSON 응답 시 |
| `request_url` | 응답 속성 | Model Property | 필수 | String (URL 형식) | `""` | 유효한 HTTP/HTTPS URL 문자열 | 상시 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-RESP-001-1**: `is_success`의 참/거짓 판별은 수학적으로 $200 \le \text{status\_code} < 300$ 범위 내에 있을 때에만 `True`로 결정한다.
- **BR-RESP-001-2**: `unwrap()` 호출 시 `is_success == True`이면 `self.data`를 즉시 반환하며, `is_success == False`이면 `ApiCallError(status_code, error, request_url)` 예외를 발생시켜야 한다.
- **BR-RESP-001-3**: `into(target_cls: Type[M]) -> M` 호출 시 `data`가 `dict` 또는 `list`일 경우 `target_cls.model_validate(self.data)`를 실행한다. 유효성 검증 실패 시 `DtoValidationError`를 발생시키며 세부 에러 트리를 첨부한다.
- **BR-RESP-001-4**: 네트워크 장애, DNS 해석 실패, 타임아웃 발생 시 라이브러리는 외부로 날것의 `httpx` 예외를 직접 전파하지 않고 `status_code=0`, `is_success=False`, `error=ApiErrorDetail(...)`을 담은 `ApiResponse`를 정상 반환하여 호출부가 단일 인터페이스로 분기할 수 있도록 보장한다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 화면 반응 및 시스템 처리 방식 | 사용자 안내 메시지 / 예외 |
| :--- | :--- | :--- |
| 응답 본문이 JSON이 아닌 HTML(502 Bad Gateway Nginx 페이지)인 경우 | `JSONDecodeError`를 포착하여 삼키고, `data=None`, `raw_text`에 HTML 본문 보존, `error.message="Failed to parse JSON body"` 바인딩 | `ApiErrorDetail(code="ERR_JSON_DECODE", message="Invalid JSON response from server")` |
| 응답 상태코드가 204 No Content인 경우 | `is_success=True`, `data=None`, `raw_text=""`, `error=None`으로 정상 반환 | 정상 처리 (예외 미발생) |
| `into(Model)` 호출 시 Pydantic 스키마 불일치 | `pydantic.ValidationError`를 포착하여 `DtoValidationError`로 래핑하고 누락/불일치 필드 목록 명시 | `DtoValidationError: Failed to deserialize response to 'UserModel': field 'email' is required` |
| `unwrap()`을 실패한 응답(`is_success=False`)에서 호출한 경우 | 즉시 `ApiCallError` 예외를 발생시켜 호출자 스택 트레이스에 실패 상태코드 및 원인 노출 | `ApiCallError: API call to https://api.example.com failed with status 404: Not Found` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 사유 | HTTP 상태 코드 매핑 | 클라이언트 표시 / 예외 형태 |
| :--- | :--- | :---: | :--- |
| `ERR_RESP_PARSE_FAILED` | 응답 본문 JSON 역직렬화 파싱 오류 | 200/500/502 | `ApiResponse.error`에 바인딩, `raw_text` 보존 |
| `ERR_DTO_VALIDATION_FAILED` | Pydantic DTO 변환 시 필드 유효성 검증 실패 | - | `DtoValidationError` 발생 |
| `ERR_HTTP_CLIENT_ERROR` | 외부 API가 4xx 클라이언트 에러 반환 | 400 ~ 499 | `ApiResponse.is_success=False`, 에러 상세 바인딩 |
| `ERR_HTTP_SERVER_ERROR` | 외부 API가 5xx 서버 에러 반환 | 500 ~ 599 | `ApiResponse.is_success=False`, 에러 상세 바인딩 |
| `ERR_NETWORK_DISCONNECTED` | DNS Lookup 실패 또는 소켓 연결 단절 | 0 | `ApiResponse.status_code=0`, 네트워크 에러 상세 |
| `ERR_REQUEST_TIMEOUT` | 요청 타임아웃(Connect/Read/Write) 발생 | 0 | `ApiResponse.status_code=0`, 타임아웃 에러 상세 |

---

### [FUNC-CONF-001] 계층형 다중 서비스 설정 로더 (Multi-Service Cascading Config Loader)

#### 1. 기본 정보
- **기능명**: 다중 서비스 계층형 설정 로더 및 클라이언트 바인딩
- **기능 ID**: `FUNC-CONF-001`
- **대응 요구사항 ID**: `REQ-CONF-001`
- **대상 모듈 코드**: `MOD-CONF-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 백엔드 엔지니어, DevOps 엔지니어

#### 2. 사전 조건 (Pre-conditions)
1. Python 런타임 환경에 `courier`가 로드된 상태.
2. 서비스 식별자(Service Name: e.g., `"default"`, `"payment"`, `"notification"`)가 지정되었거나 기본값 사용 상태.
3. 환경변수, YAML 파일, JSON 파일, 또는 코드 인자 중 하나 이상의 설정 소스가 준비된 상태.

#### 3. 사용자 인터랙션 및 시스템 동작 흐름과 플로우차트 (Step-by-Step Flow & Flowchart)
1. 호출자가 `http.get_client("payment")`를 호출한다.
2. 시스템은 내부 클라이언트 캐시(Singleton Registry)에 `"payment"` 인스턴스가 존재하는지 확인하고, 존재 시 즉시 반환한다.
3. 존재하지 않는 경우, 아래의 5단계 계층 우선순위에 따라 설정을 탐색 및 병합한다:
   - **Level 5 (Hardcoded Defaults)**: `timeout=10.0`, `connect_timeout=3.0`, `max_retries=3`, `backoff_factor=0.5`, `pool_size=20`
   - **Level 4 (JSON 파일)**: `http_clients.json`, `config.json`의 `http_clients.payment` 섹션 병합
   - **Level 3 (YAML 파일)**: `http_clients.yaml`, `http_clients.yml`, `config.yaml`의 `http_clients.payment` 섹션 병합
   - **Level 2 (환경변수)**: `HTTP_CLIENT_PAYMENT_BASE_URL`, `HTTP_CLIENT_PAYMENT_TIMEOUT` 등 `HTTP_CLIENT_{SERVICE}_*` 패턴 환경변수 병합
   - **Level 1 (명시적 인자)**: `http.get_client("payment", base_url="https://api.pay.com", timeout=5.0)`로 전달된 `kwargs` 최우선 오버라이드
4. 병합된 딕셔너리를 `HttpClientConfig` Pydantic 모델로 변환하여 유효성을 검증한다.
5. 유효성 검증 통과 시 `HttpClient` 인스턴스를 생성하고 싱글톤 레지스트리에 등록한 후 반환한다.

```mermaid
flowchart TD
    A[http.get_client(service_name) 호출] --> B{싱글톤 레지스트리에 이미 존재?}
    B -- 예 --> C[캐시된 HttpClient 인스턴스 즉시 반환]
    B -- 아니오 --> D[기본 설정 DefaultConfig 로드]
    D --> E{JSON 설정 파일 존재?}
    E -- 있음 --> F[JSON 파일 내 서비스 설정 병합]
    E -- 없음 --> G{YAML 설정 파일 존재?}
    F --> G
    G -- 있음 --> H[YAML 파일 내 서비스 설정 병합]
    G -- 없음 --> I{HTTP_CLIENT_{SERVICE}_* 환경변수 존재?}
    H --> I
    I -- 있음 --> J[환경변수 값으로 오버라이드]
    I -- 없음 --> K{명시적 kwargs 전달?}
    J --> K
    K -- 있음 --> L[kwargs로 최종 오버라이드]
    K -- 없음 --> M[HttpClientConfig Pydantic 검증]
    L --> M
    M -- 검증 실패 --> N[ConfigurationValidationError 발생]
    M -- 검증 성공 --> O[HttpClient 신규 인스턴스 생성]
    O --> P[싱글톤 레지스트리에 캐싱]
    P --> Q[생성된 HttpClient 반환]
```

#### 4. 화면 표시 및 입력 데이터 항목 명세 (Configuration Data Elements - 8대 표준 컬럼)

| 항목명 | 화면 표시/입력 구분 | UI 컴포넌트 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출/수정 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `service_name` | 함수 인자 | Python Argument | 선택 | String / `^[a-zA-Z0-9_\-]+$` | `"default"` | 영문, 숫자, 밑줄, 하이픈만 허용 | 상시 |
| `base_url` | 설정 항목 | Config Key | 선택 | String / URL 형식 | `""` | `http://` 또는 `https://` 스키마 필수 (상대 경로 호출 시 필수) | 상시 |
| `timeout` | 설정 항목 | Config Key | 선택 | Float / 0.1 ~ 300.0 (초) | `10.0` | $0.1 \le \text{timeout} \le 300.0$ | 상시 |
| `connect_timeout` | 설정 항목 | Config Key | 선택 | Float / 0.1 ~ 60.0 (초) | `3.0` | $0.1 \le \text{connect\_timeout} \le 60.0$ | 상시 |
| `max_retries` | 설정 항목 | Config Key | 선택 | Integer / 0 ~ 10 (회) | `3` | $0 \le \text{max\_retries} \le 10$ | 상시 |
| `backoff_factor` | 설정 항목 | Config Key | 선택 | Float / 0.1 ~ 10.0 | `0.5` | $0.1 \le \text{backoff\_factor} \le 10.0$ | 상시 |
| `retry_status_codes` | 설정 항목 | Config Key | 선택 | List[Integer] / 400 ~ 599 | `[429, 502, 503, 504]` | 각 요소가 유효 HTTP 에러 상태코드 | 상시 |
| `pool_size` | 설정 항목 | Config Key | 선택 | Integer / 1 ~ 500 (개) | `20` | $1 \le \text{pool\_size} \le 500$ | 상시 |
| `headers` | 설정 항목 | Config Key | 선택 | Dict[str, str] | `{}` | Key-Value 문자열 쌍 | 헤더 주입 필요 시 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-CONF-001-1**: 설정 우선순위는 `명시적 인자(kwargs) > 환경변수(ENV) > YAML > JSON > 기본값(Defaults)` 순서로 키 단위 병합(Deep Merge)되어야 한다.
- **BR-CONF-001-2**: `service_name`은 대소문자를 구분하지 않으며, 소문자로 정규화(Case-insensitive normalization)하여 관리한다 (`"PAYMENT"` == `"payment"`).
- **BR-CONF-001-3**: `base_url`의 마지막 문자가 `/`로 끝나고 호출 경로의 시작 문자가 `/`인 경우, URL 결합 시 중복 슬래시(`//`)가 발생하지 않도록 단일 슬래시로 정규화한다.
- **BR-CONF-001-4**: 동일한 `service_name`에 대해 생성된 `HttpClient`는 프로세스 내 전역 싱글톤으로 유지되어 커넥션 풀을 안전하게 공유한다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 화면 반응 및 시스템 처리 방식 | 사용자 안내 메시지 / 예외 |
| :--- | :--- | :--- |
| YAML/JSON 설정 파일 문법 에러 시 | 파싱 에러를 포착하여 구체적인 파일 경로와 라인 번호가 포함된 `ConfigParseError` 발생 | `ConfigParseError: Failed to parse YAML config at 'courier.yaml' (line 5, column 2)` |
| `base_url`에 `http://` 또는 `https://`가 누락된 경우 | Pydantic 스키마 검증에서 차단 | `ConfigurationValidationError: base_url must start with 'http://' or 'https://'` |
| 환경변수 값이 비어있는 문자열(`HTTP_CLIENT_PAYMENT_TIMEOUT=""`)인 경우 | 빈 문자열은 무시하고 하위 우선순위(YAML 또는 기본값) 유지 | 정상 처리 (기본값 10.0 적용) |
| 미등록 서비스 이름을 요청하였으나 설정 파일에 없는 경우 | 기본값(Defaults) 및 `default` 서비스 설정을 상속하여 새 클라이언트 생성 | 정상 처리 (DefaultConfig 적용) |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 사유 | HTTP 상태 코드 매핑 | 클라이언트 표시 / 예외 형태 |
| :--- | :--- | :---: | :--- |
| `ERR_CONF_SYNTAX_INVALID` | YAML/JSON 파일 포맷 파싱 오류 | - | `ConfigParseError` 발생 |
| `ERR_CONF_VALIDATION_FAILED` | 설정 필드 값 범위 또는 타입 검증 실패 | - | `ConfigurationValidationError` 발생 |
| `ERR_CONF_INVALID_URL` | `base_url` 형식 불일치 | - | `ConfigurationValidationError` 발생 |

---

### [FUNC-ENG-001] HTTPX 코어 클라이언트 (HTTPX Core Engine & Connection Pool)

#### 1. 기본 정보
- **기능명**: HTTPX 기반 동기/비동기 코어 엔진 및 커넥션 풀 라이프사이클
- **기능 ID**: `FUNC-ENG-001`
- **대응 요구사항 ID**: `REQ-ENG-001`
- **대상 모듈 코드**: `MOD-ENGINE-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 백엔드 개발자, 비동기(FastAPI/AsyncIO) 및 동기(Flask/Celery) 워커

#### 2. 사전 조건 (Pre-conditions)
1. `HttpClientConfig` 유효성 검증이 완료된 상태.
2. Python `httpx` 패키지가 런타임에 설치되어 있는 상태.

#### 3. 사용자 인터랙션 및 시스템 동작 흐름과 플로우차트 (Step-by-Step Flow & Flowchart)
1. 호출자가 동기 메서드(`client.get(...)`, `client.post(...)`) 또는 비동기 메서드(`await client.async_get(...)`, `await client.async_post(...)`)를 호출한다.
2. 시스템은 `httpx.Limits(max_connections=pool_size, max_keepalive_connections=pool_size // 2, keepalive_expiry=30.0)` 및 세분화된 타임아웃(`httpx.Timeout(timeout, connect=connect_timeout)`)을 가진 내부 클라이언트를 지연(Lazy) 초기화한다.
3. 요청 전 인터셉터를 실행하여 전역 헤더(`User-Agent`, `Authorization`), Correlation-ID(`X-Request-ID`)를 주입한다.
4. 요청을 발송하고, 장애 발생 시 `FUNC-RETY-001` 재시도 루프로 전달한다.
5. 응답 본문을 안전하게 읽고 `ApiResponse[T]`로 패키징하여 반환한다.
6. 프로세스 종료 시그널(`SIGTERM`, `SIGINT`) 또는 인터프리터 종료 시 `atexit` 훅이 작동하여 열려 있는 커넥션 풀을 `client.close()` 및 `async_client.aclose()`로 정리한다.

```mermaid
flowchart TD
    A[요청 메서드 호출: get / async_get] --> B{동기 vs 비동기 모드?}
    B -- 동기 Sync --> C[내부 httpx.Client 획득]
    B -- 비동기 Async --> D[내부 httpx.AsyncClient 획득]
    C --> E[Limits & Timeout 파라미터 확인]
    D --> E
    E --> F[인터셉터: 헤더 주입 및 Request-ID 생성]
    F --> G[HTTP 요청 전송]
    G --> H{성공 또는 재시도 대상 에러?}
    H -- 재시도 대상 에러 --> I[FUNC-RETY-001 재시도 평가 및 대기]
    I --> G
    H -- 최종 성공 또는 소진 --> J[ApiResponse[T] 생성]
    J --> K[호출자에게 반환]
    L[프로세스 종료 이벤트 / atexit] --> M[모든 활성 클라이언트 close/aclose 수행]
    M --> N[소켓 리소스 완전 해제]
```

#### 4. 화면 표시 및 입력 데이터 항목 명세 (API Call Data Elements - 8대 표준 컬럼)

| 항목명 | 화면 표시/입력 구분 | UI 컴포넌트 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출/수정 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `method` | 함수 인자 | Python Argument | 필수 | Enum ('GET', 'POST', 'PUT', 'DELETE', 'PATCH') | - | 지원 HTTP 메서드 목록 준수 | 상시 |
| `url` | 함수 인자 | Python Argument | 필수 | String | - | 공백 제외 1자 이상, 상대경로 또는 절대 URL | 상시 |
| `params` | 함수 인자 | Python Argument | 선택 | `Optional[Dict[str, Any]]` | `None` | Key-Value 쿼리 매핑 | 쿼리 파라미터 필요 시 |
| `json` | 함수 인자 | Python Argument | 선택 | `Optional[Union[Dict, List, BaseModel]]` | `None` | JSON 직렬화 가능 객체 또는 Pydantic 모델 | Body 페이로드 전송 시 |
| `data` | 함수 인자 | Python Argument | 선택 | `Optional[Union[Dict, bytes]]` | `None` | 폼 데이터 또는 바이너리 바이트 스트림 | Multipart/Form 전송 시 |
| `headers` | 함수 인자 | Python Argument | 선택 | `Optional[Dict[str, str]]` | `None` | Key-Value 헤더 매핑 | 개별 요청 헤더 추가 시 |
| `timeout` | 함수 인자 | Python Argument | 선택 | `Optional[Union[float, httpx.Timeout]]` | `None` | $0.1 \le \text{timeout} \le 300.0$ | 개별 요청 타임아웃 오버라이드 시 |
| `files` | 함수 인자 | Python Argument | 선택 | `Optional[Dict[str, Any]]` | `None` | 파일 업로드 객체 매핑 | 파일 업로드 시 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-ENG-001-1**: 단일 `HttpClient` 인스턴스에서 동기 메서드(`get`, `post` 등)와 비동기 메서드(`async_get`, `async_post` 등)를 모두 지원하며, 각각 독립된 `httpx.Limits` 풀을 유지하되 동일한 설정을 공유한다.
- **BR-ENG-001-2**: `json` 파라미터로 Pydantic `BaseModel` 인스턴스가 전달된 경우, 시스템은 자동으로 `model.model_dump(mode='json')`을 수행하여 JSON 직렬화한다.
- **BR-ENG-001-3**: 비동기 호출 시 이벤트 루프가 닫히거나 변경되는 경우(`RuntimeError: Event loop is closed`), 새 이벤트 루프에 맞추어 `httpx.AsyncClient`를 안전하게 재생성하여 코루틴 중단을 방지한다.
- **BR-ENG-001-4**: 프로세스 종료 시 `atexit` 훅을 통해 모든 열린 소켓 풀을 `close()`하여 OS 파일 디스크립터 누수를 원천 방지한다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 화면 반응 및 시스템 처리 방식 | 사용자 안내 메시지 / 예외 |
| :--- | :--- | :--- |
| DNS 조회 실패 (`httpx.ConnectError`) | `ApiResponse(status_code=0, is_success=False)` 생성, `error.code="ERR_DNS_LOOKUP_FAILED"` 바인딩 | `ApiErrorDetail: Failed to resolve host name` |
| 연결 핸드셰이크 타임아웃 (`httpx.ConnectTimeout`) | `connect_timeout`(기본 3.0s) 초과 시 즉시 차단 후 재시도 평가 | `ApiErrorDetail: Connection timeout after 3.0s` |
| 응답 읽기 타임아웃 (`httpx.ReadTimeout`) | `timeout`(기본 10.0s) 초과 시 즉시 연결을 끊고 `status_code=0` 반환 | `ApiErrorDetail: Read timeout after 10.0s` |
| 커넥션 풀 고갈 (`httpx.PoolTimeout`) | 풀 대기 큐에서 대기 시간 초과 시 소켓 누수 진단 정보와 함께 에러 반환 | `ApiErrorDetail: Connection pool exhausted (max 20)` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 사유 | HTTP 상태 코드 매핑 | 클라이언트 표시 / 예외 형태 |
| :--- | :--- | :---: | :--- |
| `ERR_ENG_CONNECT_FAILED` | 대상 서버 소켓 연결 거부 또는 DNS 실패 | 0 | `ApiResponse.error` 바인딩 |
| `ERR_ENG_TIMEOUT` | 커넥트/리드/라이트 타임아웃 발생 | 0 | `ApiResponse.error` 바인딩 |
| `ERR_ENG_POOL_EXHAUSTED` | 가용 커넥션 풀 고갈로 인한 획득 실패 | 0 | `ApiResponse.error` 바인딩 |
| `ERR_ENG_PROTOCOL_ERROR` | 비정상 HTTP 프로토콜 응답 수신 | 0 | `ApiResponse.error` 바인딩 |

---

### [FUNC-RETY-001] 지수 백오프 및 지터(Jitter) 스마트 리트라이 (Exponential Backoff with Jitter Retry Engine)

#### 1. 기본 정보
- **기능명**: 지수 백오프 및 무작위 지터 기반 스마트 자동 재시도
- **기능 ID**: `FUNC-RETY-001`
- **대응 요구사항 ID**: `REQ-RETY-001`
- **대상 모듈 코드**: `MOD-RETRY-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 클라이언트 코어 엔진, 외부 API 연동 호출자

#### 2. 사전 조건 (Pre-conditions)
1. HTTP 요청 발송 후 네트워크 예외(ConnectError, Timeout) 또는 대상 재시도 상태코드(`retry_status_codes`)가 발생한 상태.
2. 현재 시도 횟수 $k$가 최대 재시도 횟수 $K_{max}$ 미만인 상태 ($0 \le k < K_{max}$).

#### 3. 사용자 인터랙션 및 시스템 동작 흐름과 플로우차트 (Step-by-Step Flow & Flowchart)
1. 요청 실행 후 반환된 결과(상태코드 $S$ 또는 예외 $E$)를 평가한다.
2. 재시도 대상 조건 검사:
   - $S \in \{429, 502, 503, 504\}$ 이거나 $E \in \{\text{ConnectTimeout}, \text{ReadTimeout}, \text{ConnectError}\}$ 인지 확인한다.
   - HTTP 메서드가 Idempotent(GET, HEAD, PUT, DELETE, OPTIONS)인지 검사한다. `POST`나 `PATCH`인 경우 `retry_on_post=True` 설정이 명시되지 않으면 재시도를 건너뛴다.
3. 조건 미충족 또는 $k \ge K_{max}$ 이면 재시도를 중단하고 최종 결과를 반환한다.
4. 조건 충족 시 다음 대기 시간 $T_{wait}$을 수학적으로 계산한다:
   - 지수 백오프 상한: $T_{exp} = \min(T_{max}, \text{backoff\_factor} \times 2^{k})$
   - 풀 지터(Full Jitter): $T_{wait} = \text{Uniform}(0, T_{exp})$
   - 만약 응답 헤더에 `Retry-After: <seconds>`가 명시된 경우: $T_{wait} = \max(T_{wait}, \text{int}(Retry-After))$
5. 계산된 $T_{wait}$초 동안 대기한다 (동기: `time.sleep`, 비동기: `asyncio.sleep`).
6. 재시도 횟수 $k \leftarrow k + 1$ 증가 후 1단계로 돌아가 요청을 재전송한다.

```mermaid
flowchart TD
    A[요청 결과 평가] --> B{재시도 조건 충족 여부}
    B -- 조건: 429/502/503/504 또는 타임아웃? --> C{Idempotent 메서드 or retry_on_post?}
    B -- 정상 2xx 또는 일반 4xx --> Z[최종 ApiResponse 반환]
    C -- 아니오 (POST 등) --> Z
    C -- 예 --> D{현재 시도 횟수 k < max_retries?}
    D -- 소진됨 (k >= max_retries) --> Z
    D -- 재시도 가능 --> E[지수 백오프 상한 계산: T_exp = min(T_max, factor * 2^k)]
    E --> F[Full Jitter 적용: T_wait = Uniform(0, T_exp)]
    F --> G{응답에 Retry-After 헤더 존재?}
    G -- 있음 --> H[T_wait = max(T_wait, Retry-After)]
    G -- 없음 --> I[대기 수행: sleep / asyncio.sleep(T_wait)]
    H --> I
    I --> J[k = k + 1 증가 후 요청 재전송]
    J --> A
```

#### 4. 화면 표시 및 입력 데이터 항목 명세 (Retry Configuration Data Elements - 8대 표준 컬럼)

| 항목명 | 화면 표시/입력 구분 | UI 컴포넌트 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출/수정 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `max_retries` | 설정 파라미터 | Config Key | 필수 | Integer / 0 ~ 10 | `3` | $0 \le \text{max\_retries} \le 10$ | 상시 |
| `backoff_factor` | 설정 파라미터 | Config Key | 필수 | Float / 0.1 ~ 10.0 | `0.5` | $0.1 \le \text{backoff\_factor} \le 10.0$ | 상시 |
| `max_backoff_seconds` | 설정 파라미터 | Config Key | 선택 | Float / 1.0 ~ 300.0 | `30.0` | $1.0 \le \text{max\_backoff_seconds} \le 300.0$ | 상시 |
| `retry_status_codes` | 설정 파라미터 | Config Key | 선택 | List[Integer] / 400 ~ 599 | `[429, 502, 503, 504]` | 각 요소가 유효 HTTP 에러 상태코드 | 상시 |
| `retry_on_post` | 설정 파라미터 | Config Key | 선택 | Boolean | `False` | Boolean 타입 | POST 중복 실행 방어 시 |
| `respect_retry_after`| 설정 파라미터 | Config Key | 선택 | Boolean | `True` | Boolean 타입 | 429 헤더 규약 준수 시 |
| `jitter_type` | 설정 파라미터 | Config Key | 선택 | Enum ('FULL', 'EQUAL', 'NONE') | `'FULL'` | 유효 지터 전략 매칭 | 상시 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-RETY-001-1**: 대기 시간 계산은 Thundering Herd 방지를 위해 Full Jitter 공식을 기본 적용한다:
  $$T_{exp} = \min(T_{max}, \text{backoff\_factor} \times 2^{k}), \quad T_{wait} \sim \text{Uniform}(0, T_{exp})$$
- **BR-RETY-001-2**: 대상 서버가 `429 Too Many Requests` 또는 `503 Service Unavailable`과 함께 `Retry-After` 헤더를 반환한 경우, $T_{wait}$은 $\max(T_{wait}, \text{Retry-After})$를 적용한다. 단, `Retry-After` 값이 `max_backoff_seconds`를 초과하면 재시도를 포기하고 즉시 실패를 반환한다.
- **BR-RETY-001-3**: `POST`, `PATCH` 등 비멱등(Non-idempotent) 요청은 결제 중복 및 중복 생성 사고 방지를 위해 `retry_on_post=True`가 명시되지 않는 한 자동 재시도를 수행하지 않는다.
- **BR-RETY-001-4**: 모든 재시도 시도가 소진된 후 반환되는 `ApiResponse`의 `duration_ms`는 전체 재시도 대기 시간과 네트워크 통신 소요 시간의 누적 합산값이어야 한다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 화면 반응 및 시스템 처리 방식 | 사용자 안내 메시지 / 예외 |
| :--- | :--- | :--- |
| `Retry-After` 헤더가 잘못된 문자열이거나 음수인 경우 | 파싱 에러를 무시하고 표준 지수 백오프 공식($T_{wait}$)으로 폴백 | 정상 지수 백오프 대기 적용 |
| 재시도 중 프로세스 종료 시그널(`SIGINT`/`SIGTERM`) 수신 시 | 즉시 `asyncio.CancelledError` 또는 인터럽트를 전파하여 대기를 즉시 중단 | 프로세스 즉시 종료 |
| 백오프 대기 시간이 지나치게 길어지는 경우 | `max_backoff_seconds`(30.0s)를 상한선으로 강제 클램핑 | 대기 시간 상한 30초 고정 |
| 재시도 최대 횟수 도달 후에도 실패 지속 시 | 마지막 응답 또는 에러를 `ApiResponse`로 포장하고 `error.code="ERR_RETRY_EXHAUSTED"` 주입 | `ApiErrorDetail: Request failed after 3 retry attempts` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 사유 | HTTP 상태 코드 매핑 | 클라이언트 표시 / 예외 형태 |
| :--- | :--- | :---: | :--- |
| `ERR_RETRY_EXHAUSTED` | 최대 재시도 횟수 초과 후 최종 실패 | 429, 502, 503, 504 등 | `ApiResponse.error` 바인딩 |
| `ERR_RETRY_AFTER_EXCEEDED` | `Retry-After` 대기 시간이 `max_backoff_seconds` 초과 | 429 | `ApiResponse.error` 바인딩 |
| `ERR_RETRY_NON_IDEMPOTENT_BLOCKED` | POST 요청 재시도 차단 | 500, 502 등 | `ApiResponse.error` 바인딩 |
