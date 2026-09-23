# [courier] HTTP 클라이언트 및 통일 응답 상세기능정의서 (Modular FSD)

- **도메인**: HTTP 클라이언트 자동 구성 및 통일 응답 처리
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.1 (Humanizer 지침 반영 개정판)
- **상태**: Approved

---

## 단위 기능 상세 명세 (단위기능별 7대 상세 명세 완비)

---

### [FUNC-RESP-001] 통일된 제네릭 응답 모델 `ApiResponse[T]` (Unified Generic ApiResponse Wrapper)

#### 1. 기본 정보
- **기능명**: 통일된 제네릭 응답 객체 `ApiResponse[T]` 및 Result 제어
- **기능 ID**: `FUNC-RESP-001`
- **대응 요구사항 ID**: `REQ-RESP-001`, `REQ-DTO-001`
- **대상 모듈 코드**: `MOD-RESP-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 사내 백엔드 개발자, 데이터 엔지니어

#### 2. 사전 조건 (Pre-conditions)
1. Courier 클라이언트(`HttpClient`)를 통해 동기 또는 비동기 요청이 완료된 상태.
2. 서버로부터 HTTP 응답(`httpx.Response`)을 수신했거나, 네트워크 단절/타임아웃 등 소켓 계층 예외가 포착된 상태.
3. 요청 발송 시점부터 완료 시점까지의 고정밀 소요 시간(`time.perf_counter()`)이 밀리초 단위로 측정된 상태.

#### 3. 시스템 동작 흐름 및 플로우차트 (Step-by-Step Flow & Flowchart)

호출자가 `client.get(...)` 또는 `await client.async_get(...)`을 호출하면 내부에서 다음 단계로 응답을 정규화합니다:

1. **타이머 측정 및 요청 발송**: 요청 발송 직전 $t_{start}$를 기록하고 완료 시점 $t_{end}$와의 차이로 소요 시간 $\Delta t = (t_{end} - t_{start}) \times 1000$ (ms)를 산출합니다.
2. **응답 수신 여부 분기**:
   - **정상 수신 ($S \ge 100$)**:
     - $200 \le S < 300$ (성공): `is_success = True`로 설정하고 본문을 JSON 파싱하여 `data`에 할당합니다. 빈 본문(204 No Content)이거나 파싱 불가 시 `data = None`, 원시 문자열은 `raw_text`에 보존합니다. `error = None`으로 초기화합니다.
     - $S \ge 300$ (실패): `is_success = False`로 설정하고, 벤더 응답 본문(`{"message": ...}` 등)을 분석하여 `ApiErrorDetail(code=..., message=..., details=...)`을 채웁니다.
   - **소켓 실패 / 타임아웃 ($S = 0$)**:
     - DNS 실패, 연결 거부, 읽기 타임아웃 발생 시 호출자에게 즉시 예외를 던져 프로세스를 죽이지 않습니다.
     - `status_code = 0`, `is_success = False`, `data = None`, `error = ApiErrorDetail(code="ERR_NETWORK_DISCONNECTED" 또는 "ERR_REQUEST_TIMEOUT", message=str(exc))`를 담은 `ApiResponse`를 정상 반환합니다.
3. **호출자 소비 흐름**:
   - 호출자는 `if res.is_success:` 조건문으로 분기하거나, 실패 시 즉시 중단하길 원할 경우 `res.unwrap()`을 호출하여 `data`를 꺼냅니다 (`is_success=False`이면 `ApiCallError` 발생).
   - 검증된 DTO로 변환하고자 할 때 `res.into(UserModel)`을 호출하여 Pydantic 모델 인스턴스를 바로 취득합니다.

```mermaid
flowchart TD
    A[HTTP 요청 실행] --> B[소요 시간 duration_ms 측정]
    B --> C{응답 수신 성공?}
    C -- 소켓 실패/타임아웃 --> D[status_code=0, is_success=False]
    D --> E[ApiErrorDetail에 예외 메시지 바인딩]
    C -- HTTP 응답 수신 --> F{상태 코드 200 <= status < 300?}
    F -- 성공 (2xx) --> G[is_success=True, error=None]
    G --> H{본문 JSON 파싱}
    H -- 성공 --> I[data에 딕셔너리/리스트 할당]
    H -- 실패/빈 본문 --> J[raw_text 보존 및 data=None]
    F -- 실패 (3xx/4xx/5xx) --> K[is_success=False]
    K --> L[에러 본문 파싱하여 ApiErrorDetail 생성]
    E --> M[ApiResponse[T] 인스턴스 반환]
    I --> M
    J --> M
    L --> M
    M --> N{호출자 제어 방식}
    N -- if res.is_success --> O[안전한 if/else 비즈니스 분기]
    N -- res.unwrap() --> P[성공 시 data 반환 / 실패 시 ApiCallError 발생]
    N -- res.into(Model) --> Q[Pydantic v2 model_validate 수행]
```

#### 4. 데이터 항목 명세 (Data Elements - 8대 표준 컬럼)

| 항목명 | 입출력 구분 | 속성/타입 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출 및 오버라이드 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `status_code` | 반환 속성 | Model Property | 필수 | Integer (0 ~ 599) | `0` | 0은 네트워크 실패, 100~599는 HTTP 상태코드 | 항상 제공 |
| `is_success` | 반환 속성 | Model Property | 필수 | Boolean | `False` | $200 \le \text{status\_code} < 300$일 때만 True | 항상 제공 |
| `data` | 반환 속성 | Model Property | 선택 | Generic `Optional[T]` | `None` | 성공 시 파싱된 JSON 본문, 실패 시 None | `is_success=True`일 때 유효 |
| `error` | 반환 속성 | Model Property | 선택 | `Optional[ApiErrorDetail]` | `None` | 실패 시 에러 코드, 메시지, 상세 딕셔너리 | `is_success=False`일 때 제공 |
| `duration_ms` | 반환 속성 | Model Property | 필수 | Float | `0.0` | 0 이상 실수, 소수점 둘째자리 반올림 | 항상 제공 |
| `headers` | 반환 속성 | Model Property | 필수 | `Dict[str, str]` | `{}` | 대소문자 무시(Case-insensitive) 딕셔너리 | 항상 제공 |
| `raw_text` | 반환 속성 | Model Property | 선택 | `Optional[str]` | `None` | 원시 문자열 본문 (최대 1MB 버퍼링) | 디버깅 및 비JSON 응답 시 제공 |
| `request_url` | 반환 속성 | Model Property | 필수 | String | `""` | 유효한 HTTP/HTTPS URL 문자열 | 항상 제공 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-RESP-001-1**: `is_success` 판별식은 엄격히 $200 \le \text{status\_code} < 300$을 준수합니다. 301/302 리다이렉트는 클라이언트 엔진 내부에서 최종 목적지까지 추적한 후의 최종 상태코드를 기준으로 판정합니다.
- **BR-RESP-001-2**: `unwrap()`은 함수형 언어의 Result 언래핑 규칙을 따릅니다. 성공 응답에서는 `self.data`를 그대로 반환하며, 실패 응답에서는 `ApiCallError(status_code, error, request_url)`를 발생시켜 별도 if문 없이 빠른 실패(Fast-Fail)가 가능하도록 합니다.
- **BR-RESP-001-3**: `into(target_model: Type[M]) -> M`은 Pydantic v2의 `model_validate`를 사용합니다. 검증 실패 시 Pydantic의 원시 예외를 그대로 전파하지 않고 `DtoValidationError`로 래핑하여 어떤 필드에서 불일치가 났는지 원인을 요약해 반환합니다.
- **BR-RESP-001-4**: 소켓 연결 실패나 타임아웃 발생 시 Courier는 날것의 `httpx.TransportError`를 상위로 던지지 않고 `status_code=0`, `is_success=False`로 포장합니다. 이를 통해 호출자는 외부 API가 다운되었을 때도 503 응답과 완전히 동일한 `if not res.is_success:` 코드로 우아하게 폴백할 수 있습니다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 시스템 처리 방식 | 호출자 수신 객체 / 예외 |
| :--- | :--- | :--- |
| Nginx 502 Bad Gateway로 HTML 페이지가 수신된 경우 | `JSONDecodeError`를 조용히 흡수하고 `data=None`, `raw_text`에 HTML 앞부분 보존, `error.message`에 안내 기록 | `ApiResponse(status_code=502, is_success=False, error=ApiErrorDetail(code="ERR_RESP_PARSE_FAILED"))` |
| 204 No Content로 본문이 아예 없는 경우 | 에러가 아니므로 `is_success=True`, `data=None`, `raw_text=""`, `error=None`으로 반환 | 정상 성공 객체 반환 |
| `into(Model)` 호출 시 외부 API가 필수 필드를 누락한 경우 | `pydantic.ValidationError`를 포착하여 누락 필드 경로와 함께 `DtoValidationError` 발생 | `DtoValidationError: Field 'user_id' is missing in response from https://api.pay.com` |
| 실패한 응답에서 실수로 `unwrap()`을 호출한 경우 | 호출 스택과 상태코드를 보존한 `ApiCallError` 예외를 던져 버그 위치를 즉시 인지하도록 유도 | `ApiCallError: API call failed with status 404: Resource not found` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 원인 | HTTP 상태코드 매핑 | 반환 형태 |
| :--- | :--- | :---: | :--- |
| `ERR_RESP_PARSE_FAILED` | 응답 본문 JSON 역직렬화 실패 | 200, 500, 502 등 | `ApiResponse.error` 필드에 바인딩 |
| `ERR_DTO_VALIDATION_FAILED` | Pydantic 스키마 검증 실패 | - | `DtoValidationError` 예외 발생 |
| `ERR_HTTP_CLIENT_ERROR` | 외부 API 4xx 클라이언트 에러 | 400 ~ 499 | `ApiResponse.error` 필드에 바인딩 |
| `ERR_HTTP_SERVER_ERROR` | 외부 API 5xx 서버 에러 | 500 ~ 599 | `ApiResponse.error` 필드에 바인딩 |
| `ERR_NETWORK_DISCONNECTED` | DNS 오류 또는 호스트 소켓 연결 실패 | 0 | `ApiResponse(status_code=0)` 반환 |
| `ERR_REQUEST_TIMEOUT` | Connect 또는 Read 타임아웃 초과 | 0 | `ApiResponse(status_code=0)` 반환 |

---

### [FUNC-CONF-001] 계층형 다중 서비스 설정 로더 (Multi-Service Cascading Config Loader)

#### 1. 기본 정보
- **기능명**: 다중 서비스 계층형 설정 로더 및 클라이언트 바인딩
- **기능 ID**: `FUNC-CONF-001`
- **대응 요구사항 ID**: `REQ-CONF-001`
- **대상 모듈 코드**: `MOD-CONF-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 백엔드 개발자, DevOps/SRE 엔지니어

#### 2. 사전 조건 (Pre-conditions)
1. Python 실행 환경에 `courier` 패키지가 임포트된 상태.
2. 호출 시 서비스 이름(예: `"payment"`, `"notification"`)이 전달되었거나 기본값(`"default"`)을 사용하는 상태.

#### 3. 시스템 동작 흐름 및 플로우차트 (Step-by-Step Flow & Flowchart)

1. 호출자가 `http.get_client("payment")`를 호출합니다.
2. 내부 싱글톤 레지스트리(In-Memory Registry)에 이미 생성된 `"payment"` 클라이언트가 있는지 확인하고, 있으면 즉시 재사용하여 반환합니다.
3. 최초 호출인 경우, 5단계 우선순위 규칙에 따라 설정을 수집하고 딕셔너리 딥 머지(Deep Merge)를 수행합니다:
   - **1순위 (명시적 인자)**: `http.get_client("payment", base_url="...", timeout=5.0)`로 넘긴 `kwargs`
   - **2순위 (환경변수)**: `COURIER_PAYMENT_BASE_URL`, `COURIER_PAYMENT_TIMEOUT` 등 `COURIER_{SERVICE}_*` 환경변수
   - **3순위 (YAML 파일)**: 작업 디렉토리의 `courier.yaml`, `courier.yml`, `config.yaml` 내 `payment` 섹션
   - **4순위 (JSON 파일)**: `courier.json`, `config.json` 내 `payment` 섹션
   - **5순위 (기본값 Defaults)**: `timeout=10.0`, `connect_timeout=3.0`, `max_retries=3`, `backoff_factor=0.5`, `pool_size=20`
4. 최종 병합된 설정값을 `HttpClientConfig` Pydantic 모델로 변환하여 유효성을 검증합니다.
5. 유효성 검증을 통과하면 새 `HttpClient` 인스턴스를 생성하여 레지스트리에 캐싱하고 호출자에게 반환합니다.

```mermaid
flowchart TD
    A[http.get_client(service_name) 호출] --> B{레지스트리에 이미 존재?}
    B -- 예 --> C[캐시된 싱글톤 인스턴스 반환]
    B -- 아니오 --> D[기본 설정 DefaultConfig 적재]
    D --> E{JSON 파일 존재?}
    E -- 있음 --> F[JSON 설정 병합]
    E -- 없음 --> G{YAML 파일 존재?}
    F --> G
    G -- 있음 --> H[YAML 설정 병합]
    G -- 없음 --> I{COURIER_{SERVICE}_* ENV 존재?}
    H --> I
    I -- 있음 --> J[환경변수로 오버라이드]
    I -- 없음 --> K{명시적 kwargs 전달?}
    J --> K
    K -- 있음 --> L[kwargs로 최종 오버라이드]
    K -- 없음 --> M[HttpClientConfig Pydantic 검증]
    L --> M
    M -- 실패 --> N[ConfigurationValidationError 발생]
    M -- 성공 --> O[새 HttpClient 생성 및 레지스트리 캐싱]
    O --> P[인스턴스 반환]
```

#### 4. 데이터 항목 명세 (Configuration Data Elements - 8대 표준 컬럼)

| 항목명 | 입출력 구분 | 속성/타입 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출 및 오버라이드 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `service_name` | 함수 인자 | Python Arg | 선택 | String / 영문, 숫자, 밑줄, 하이픈 | `"default"` | 정규식 `^[a-zA-Z0-9_\-]+$` | 항상 사용 가능 |
| `base_url` | 설정 항목 | Config Key | 선택 | String / URL 형식 | `""` | `http://` 또는 `https://` 필수 (상대경로 호출 시 필수) | 항상 오버라이드 가능 |
| `timeout` | 설정 항목 | Config Key | 선택 | Float / 0.1 ~ 300.0 (초) | `10.0` | $0.1 \le \text{timeout} \le 300.0$ | 항상 오버라이드 가능 |
| `connect_timeout` | 설정 항목 | Config Key | 선택 | Float / 0.1 ~ 60.0 (초) | `3.0` | $0.1 \le \text{connect\_timeout} \le 60.0$ | 항상 오버라이드 가능 |
| `max_retries` | 설정 항목 | Config Key | 선택 | Integer / 0 ~ 10 (회) | `3` | $0 \le \text{max\_retries} \le 10$ | 항상 오버라이드 가능 |
| `backoff_factor` | 설정 항목 | Config Key | 선택 | Float / 0.1 ~ 10.0 | `0.5` | $0.1 \le \text{backoff\_factor} \le 10.0$ | 항상 오버라이드 가능 |
| `retry_status_codes` | 설정 항목 | Config Key | 선택 | List[Integer] | `[429, 502, 503, 504]` | 각 요소가 400~599 사이 정수 | 항상 오버라이드 가능 |
| `pool_size` | 설정 항목 | Config Key | 선택 | Integer / 1 ~ 500 | `20` | $1 \le \text{pool\_size} \le 500$ | 항상 오버라이드 가능 |
| `headers` | 설정 항목 | Config Key | 선택 | Dict[str, str] | `{}` | Key-Value 문자열 쌍 | 공통 헤더 주입 시 활용 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-CONF-001-1**: 설정 병합은 `kwargs > ENV > YAML > JSON > Defaults` 순서를 엄격히 준수합니다. 하위 레벨의 값은 상위 레벨에 동일 키가 없을 때만 폴백으로 사용됩니다.
- **BR-CONF-001-2**: 서비스 이름은 대소문자를 구분하지 않습니다. `"Payment"`, `"PAYMENT"`, `"payment"`는 모두 소문자로 정규화되어 동일한 싱글톤 풀을 바라봅니다.
- **BR-CONF-001-3**: `base_url` 끝이 `/`로 끝나고 호출 경로가 `/`로 시작할 때, URL 결합 시 슬래시가 두 개(`//`)가 되지 않도록 시스템이 자동으로 단일 슬래시로 정규화합니다.
- **BR-CONF-001-4**: 미등록 서비스 이름을 요청했더라도 설정 파일에 섹션이 없으면 `default` 섹션의 설정과 안전 기본값을 상속받아 유연하게 클라이언트를 생성합니다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 시스템 처리 방식 | 사용자 안내 메시지 / 예외 |
| :--- | :--- | :--- |
| `courier.yaml` 파일 문법 오류 (들여쓰기 불량 등) | 파싱 에러 위치(파일명, 라인 번호)를 명시한 `ConfigParseError` 발생 | `ConfigParseError: Failed to parse 'courier.yaml' at line 12: mapping values are not allowed here` |
| `base_url`에 스키마 누락 (`"api.pay.com"`) | Pydantic 스키마 검증에서 즉시 차단하여 런타임 URL 오류 방어 | `ConfigurationValidationError: base_url must start with 'http://' or 'https://'` |
| 환경변수 값이 비어있는 문자열인 경우 (`COURIER_PAYMENT_TIMEOUT=""`) | 빈 문자열은 무시하고 하위 계층(YAML 또는 기본값) 유지 | 정상 처리 (기본값 10.0초 유지) |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 원인 | 예외 클래스 | 대응 가이드 |
| :--- | :--- | :--- | :--- |
| `ERR_CONF_SYNTAX_INVALID` | YAML/JSON 파일 파싱 실패 | `ConfigParseError` | 설정 파일의 YAML/JSON 문법 및 인코딩 확인 |
| `ERR_CONF_VALIDATION_FAILED` | 설정값 타입 또는 유효 범위 초과 | `ConfigurationValidationError` | timeout, pool_size 등 수치 범위 확인 |
| `ERR_CONF_INVALID_URL` | URL 스키마 누락 또는 잘못된 형식 | `ConfigurationValidationError` | http:// 또는 https:// 스키마 추가 |

---

### [FUNC-ENG-001] HTTPX 코어 클라이언트 (HTTPX Core Engine & Connection Pool)

#### 1. 기본 정보
- **기능명**: HTTPX 기반 동기/비동기 코어 엔진 및 커넥션 풀 라이프사이클
- **기능 ID**: `FUNC-ENG-001`
- **대응 요구사항 ID**: `REQ-ENG-001`
- **대상 모듈 코드**: `MOD-ENGINE-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 백엔드 개발자 (FastAPI, Celery, Django, 스크립트 작성자)

#### 2. 사전 조건 (Pre-conditions)
1. `HttpClientConfig` 유효성 검증이 완료된 상태.
2. `httpx>=0.25.0` 라이브러리가 런타임에 설치되어 있는 상태.

#### 3. 시스템 동작 흐름 및 플로우차트 (Step-by-Step Flow & Flowchart)

1. 호출자가 동기 메서드(`client.get`, `client.post`) 또는 비동기 메서드(`await client.async_get`, `await client.async_post`)를 호출합니다.
2. 엔진은 내부 `httpx.Limits(max_connections=pool_size, max_keepalive_connections=pool_size // 2, keepalive_expiry=30.0)` 설정을 적용한 `httpx.Client`(동기) 또는 `httpx.AsyncClient`(비동기)를 지연 생성(Lazy Init)합니다.
3. 요청 전 인터셉터를 통해 전역 헤더(`User-Agent`, `Authorization`)와 분산 추적용 Correlation-ID(`X-Request-ID`)를 자동 주입합니다.
4. 소켓을 통해 HTTP 요청을 전송하며, 일시 장애 발생 시 `FUNC-RETY-001` 재시도 루프로 제어를 넘깁니다.
5. 응답 수신 후 소요 시간을 기록하고 `ApiResponse[T]`로 패키징하여 반환합니다.
6. 프로세스 종료 시그널(`SIGTERM`, `SIGINT`) 또는 인터프리터 종료 시 `atexit` 훅이 작동하여 열려 있는 모든 커넥션 풀을 안전하게 닫습니다.

```mermaid
flowchart TD
    A[API 호출: get / async_get] --> B{동기 vs 비동기 구분}
    B -- 동기 Sync --> C[내부 httpx.Client 커넥션 풀 확인]
    B -- 비동기 Async --> D[내부 httpx.AsyncClient 풀 및 이벤트 루프 확인]
    C --> E[인터셉터: 헤더 주입 및 X-Request-ID 발급]
    D --> E
    E --> F[소켓 HTTP 통신 실행]
    F --> G{응답 결과 평가}
    G -- 429/5xx 또는 타임아웃 --> H[FUNC-RETY-001 재시도 평가 및 대기]
    H --> F
    G -- 성공 또는 최종 종료 --> I[ApiResponse[T] 생성]
    I --> J[호출자에게 결과 반환]
    K[프로세스 종료/SIGTERM] --> L[atexit 훅: close() 및 aclose() 일괄 수행]
    L --> M[소켓 디스크립터 완전 해제]
```

#### 4. 데이터 항목 명세 (API Call Data Elements - 8대 표준 컬럼)

| 항목명 | 입출력 구분 | 속성/타입 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출 및 오버라이드 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `method` | 함수 인자 | Python Arg | 필수 | Enum ('GET', 'POST', 'PUT', 'DELETE', 'PATCH') | - | 유효한 대문자 HTTP 메서드 | 항상 필수 |
| `url` | 함수 인자 | Python Arg | 필수 | String | - | 공백 제외 1자 이상, 상대경로 또는 절대 URL | 항상 필수 |
| `params` | 함수 인자 | Python Arg | 선택 | `Optional[Dict[str, Any]]` | `None` | Key-Value 쿼리 파라미터 | 쿼리스트링 전달 시 |
| `json` | 함수 인자 | Python Arg | 선택 | `Optional[Union[Dict, List, BaseModel]]` | `None` | JSON 직렬화 가능 객체 또는 Pydantic 모델 | 본문 전달 시 |
| `data` | 함수 인자 | Python Arg | 선택 | `Optional[Union[Dict, bytes]]` | `None` | 폼 데이터 또는 원시 바이트 스트림 | Form/바이너리 전달 시 |
| `headers` | 함수 인자 | Python Arg | 선택 | `Optional[Dict[str, str]]` | `None` | Key-Value 커스텀 헤더 맵 | 개별 요청 헤더 추가 시 |
| `timeout` | 함수 인자 | Python Arg | 선택 | `Optional[Union[float, httpx.Timeout]]` | `None` | $0.1 \le \text{timeout} \le 300.0$ | 개별 요청 타임아웃 변경 시 |
| `files` | 함수 인자 | Python Arg | 선택 | `Optional[Dict[str, Any]]` | `None` | 파일 업로드 멀티파트 맵 | 파일 전송 시 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-ENG-001-1**: 단일 `HttpClient` 인스턴스에서 동기 메서드와 비동기 메서드를 모두 지원합니다. 단, 동기 풀과 비동기 풀은 내부적으로 완전히 격리된 소켓 세션을 유지합니다.
- **BR-ENG-001-2**: `json` 파라미터로 Pydantic `BaseModel` 객체가 들어오면, 수동으로 덤프할 필요 없이 시스템이 `model.model_dump(mode='json')`을 자동 호출하여 직렬화합니다.
- **BR-ENG-001-3**: 비동기 호출 시 현재 스레드의 활성 이벤트 루프(`asyncio.get_running_loop()`)가 이전 루프와 달라졌거나 닫힌 경우(`RuntimeError`), `AsyncClient`를 투명하게 재생성하여 코루틴 크래시를 방지합니다.
- **BR-ENG-001-4**: 프로세스 종료 시 `atexit` 훅을 통해 등록된 모든 활성 클라이언트를 안전하게 종료(`close()`, `aclose()`)하여 소켓 누수를 방지합니다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 시스템 처리 방식 | 사용자 수신 객체 / 예외 |
| :--- | :--- | :--- |
| DNS 조회 실패 (`httpx.ConnectError`) | 재시도 대상(총 3회)으로 백오프 후, 최종 실패 시 `status_code=0`으로 래핑 반환 | `ApiResponse(status_code=0, error=ApiErrorDetail(code="ERR_ENG_CONNECT_FAILED"))` |
| TCP 핸드셰이크 3초 초과 (`httpx.ConnectTimeout`) | `connect_timeout` 설정값 도달 즉시 소켓을 끊고 재시도 큐로 이관 | `ApiResponse(status_code=0, error=ApiErrorDetail(code="ERR_ENG_TIMEOUT"))` |
| 풀 소켓 고갈 대기 시간 5초 초과 (`httpx.PoolTimeout`) | 가용 소켓 부족 상황을 명시하고 즉시 에러 반환 | `ApiResponse(status_code=0, error=ApiErrorDetail(code="ERR_ENG_POOL_EXHAUSTED"))` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 원인 | HTTP 상태코드 매핑 | 반환 형태 |
| :--- | :--- | :---: | :--- |
| `ERR_ENG_CONNECT_FAILED` | 호스트 연결 거부 또는 DNS 실패 | 0 | `ApiResponse.error` 바인딩 |
| `ERR_ENG_TIMEOUT` | Connect 또는 Read 시간 초과 | 0 | `ApiResponse.error` 바인딩 |
| `ERR_ENG_POOL_EXHAUSTED` | 커넥션 풀 가용 소켓 고갈 | 0 | `ApiResponse.error` 바인딩 |

---

### [FUNC-RETY-001] Full Jitter 지수 백오프 스마트 재시도 (Exponential Backoff with Full Jitter)

#### 1. 기본 정보
- **기능명**: Full Jitter 지수 백오프 기반 스마트 자동 재시도
- **기능 ID**: `FUNC-RETY-001`
- **대응 요구사항 ID**: `REQ-RETY-001`
- **대상 모듈 코드**: `MOD-RETRY-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 클라이언트 코어 엔진, 외부 API 연동 호출자

#### 2. 사전 조건 (Pre-conditions)
1. HTTP 요청 발송 후 네트워크 에러(ConnectError, Timeout) 또는 대상 재시도 상태코드(429, 502, 503, 504)를 수신한 상태.
2. 현재 시도 횟수 $k$가 최대 재시도 횟수 $K_{max}$ 미만인 상태 ($0 \le k < K_{max}$).

#### 3. 시스템 동작 흐름 및 플로우차트 (Step-by-Step Flow & Flowchart)

1. 요청 실행 결과를 평가하여 재시도 대상인지 검사합니다:
   - 상태코드 $S \in \{429, 502, 503, 504\}$ 또는 타임아웃/소켓 에러 발생 여부
   - 요청 메서드가 멱등(Idempotent: GET, HEAD, PUT, DELETE, OPTIONS)인지 확인. 비멱등(POST, PATCH)인 경우 `retry_on_post=True`가 아니면 즉시 재시도를 건너뜁니다.
2. 재시도 조건을 만족하면 Full Jitter 공식으로 대기 시간 $T_{wait}$을 산출합니다:
   $$T_{exp} = \min(T_{max}, \text{backoff\_factor} \times 2^{k})$$
   $$T_{wait} \sim \text{Uniform}(0, T_{exp})$$
3. 상대 서버가 `Retry-After: <초>` 헤더를 반환했다면 $T_{wait} = \max(T_{wait}, \text{Retry-After})$를 적용합니다 (단, `max_backoff_seconds` 초과 시 재시도 포기).
4. 계산된 시간만큼 대기(동기 `time.sleep`, 비동기 `asyncio.sleep`) 후 $k \leftarrow k + 1$로 재전송합니다.

```mermaid
flowchart TD
    A[요청 결과 수신] --> B{재시도 조건 충족?}
    B -- 429/502/503/504 또는 소켓 에러 --> C{멱등 메서드 or retry_on_post?}
    B -- 정상 2xx 또는 일반 4xx --> Z[최종 ApiResponse 반환]
    C -- 비멱등 POST (플래그 OFF) --> Z
    C -- 조건 충족 --> D{시도 횟수 k < max_retries?}
    D -- 소진됨 --> Z
    D -- 재시도 가능 --> E[T_exp = min(T_max, factor * 2^k)]
    E --> F[Full Jitter: T_wait = Uniform(0, T_exp)]
    F --> G{Retry-After 헤더 존재?}
    G -- 있음 --> H[T_wait = max(T_wait, Retry-After)]
    G -- 없음 --> I[대기: sleep 또는 asyncio.sleep]
    H --> I
    I --> J[k = k + 1 증가 후 재전송]
    J --> A
```

#### 4. 데이터 항목 명세 (Retry Configuration Data Elements - 8대 표준 컬럼)

| 항목명 | 입출력 구분 | 속성/타입 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출 및 오버라이드 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `max_retries` | 설정 항목 | Config Key | 필수 | Integer / 0 ~ 10 | `3` | $0 \le \text{max\_retries} \le 10$ | 항상 오버라이드 가능 |
| `backoff_factor` | 설정 항목 | Config Key | 필수 | Float / 0.1 ~ 10.0 | `0.5` | $0.1 \le \text{backoff\_factor} \le 10.0$ | 항상 오버라이드 가능 |
| `max_backoff_seconds` | 설정 항목 | Config Key | 선택 | Float / 1.0 ~ 300.0 | `30.0` | $1.0 \le \text{max\_backoff\_seconds} \le 300.0$ | 항상 오버라이드 가능 |
| `retry_status_codes` | 설정 항목 | Config Key | 선택 | List[Integer] | `[429, 502, 503, 504]` | 각 요소가 400~599 사이 정수 | 항상 오버라이드 가능 |
| `retry_on_post` | 설정 항목 | Config Key | 선택 | Boolean | `False` | Boolean 타입 | POST 이중 승인 방어 |
| `respect_retry_after`| 설정 항목 | Config Key | 선택 | Boolean | `True` | Boolean 타입 | 429 헤더 규약 준수 |
| `jitter_type` | 설정 항목 | Config Key | 선택 | Enum ('FULL', 'NONE') | `'FULL'` | Full Jitter 권장 | 항상 오버라이드 가능 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-RETY-001-1**: 재시도 시 고정 간격을 사용하지 않고 반드시 Full Jitter 알고리즘($\text{Uniform}(0, T_{exp})$)을 적용하여 동시 재시도로 인한 Thundering Herd 현상을 방지합니다.
- **BR-RETY-001-2**: `POST`, `PATCH` 요청은 중복 승인/중복 생성 사고를 원천 방지하기 위해 `retry_on_post=True`가 명시되지 않는 한 절대 재시도하지 않습니다.
- **BR-RETY-001-3**: `Retry-After` 헤더 값이 `max_backoff_seconds`(기본 30초)를 초과하는 경우, 시스템이 무한정 블로킹되는 것을 막기 위해 재시도를 포기하고 즉시 `ERR_RETRY_AFTER_EXCEEDED` 실패를 반환합니다.
- **BR-RETY-001-4**: 모든 재시도 소진 후 반환되는 `ApiResponse`의 `duration_ms`는 백오프 대기 시간과 네트워크 왕복 시간을 모두 포함한 실제 누적 소요 시간이어야 합니다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 시스템 처리 방식 | 사용자 수신 객체 / 예외 |
| :--- | :--- | :--- |
| `Retry-After` 헤더 값이 음수이거나 날짜 형식이 깨진 경우 | 파싱 에러를 무시하고 표준 Full Jitter 공식으로 즉시 폴백 | 정상 지수 백오프 대기 수행 |
| 재시도 대기 도중 `SIGINT` (Ctrl+C) 또는 취소 시그널 인입 | 대기 루프를 즉시 탈출하고 상위 취소 예외(`CancelledError`) 전파 | 프로세스 즉각 종료 |
| 최대 재시도(3회) 모두 소진 시 | 마지막 실패 응답을 `ApiResponse`로 포장하고 `error.code="ERR_RETRY_EXHAUSTED"` 주입 | `ApiResponse(status_code=503, error=ApiErrorDetail(code="ERR_RETRY_EXHAUSTED"))` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 원인 | HTTP 상태코드 매핑 | 반환 형태 |
| :--- | :--- | :---: | :--- |
| `ERR_RETRY_EXHAUSTED` | 최대 재시도 횟수 소진 후 최종 실패 | 429, 502, 503, 504 등 | `ApiResponse.error` 바인딩 |
| `ERR_RETRY_AFTER_EXCEEDED` | `Retry-After` 값이 최대 상한선(30초) 초과 | 429 | `ApiResponse.error` 바인딩 |
| `ERR_RETRY_NON_IDEMPOTENT_BLOCKED`| 비멱등 POST 재시도 차단 | 500, 502 등 | `ApiResponse.error` 바인딩 |
