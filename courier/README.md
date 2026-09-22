# courier

> **High-Resilience External API Courier for Python (HTTPX & Pydantic v2)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![HTTPX](https://img.shields.io/badge/httpx-0.28+-orange.svg)](https://www.encode.io/httpx/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-green.svg)](https://docs.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`courier`는 외부(External) API를 연동할 때 발생하는 복잡한 보일러플레이트(세션 생성, 커넥션 풀링, 지수 백오프 재시도, 에러 파싱, 타임아웃 등)를 제거하고, **외부 서비스와의 요청과 응답을 신속하고 안전하게 배달(Courier)하며 언제나 예측 가능한 표준화된 `ApiResponse[T]`를 보장하는 고신뢰성 파이썬 HTTP 클라이언트 프레임워크**입니다.

Java의 OpenFeign/Retrofit과 Go의 Resty 등 현대 언어들의 뛰어난 HTTP 라이브러리 설계 철학을 파이써닉한 Result 패턴으로 융합하였습니다.

---

## ✨ 핵심 기능 (Key Features)

- **통일된 응답 모델 (`ApiResponse[T]` - Result 패턴)**:
  - 어떤 장애나 4xx/5xx 상황에서도 앱이 크래시되지 않고 일관된 `ApiResponse` 객체 반환 (`is_success`, `status_code`, `data`, `error`, `duration_ms`).
  - `res.unwrap()`: 성공 시 데이터 반환, 실패 시 구체적인 `ApiCallError` 예외 발생.
  - `res.into(UserModel)`: Pydantic v2 모델로 한 줄에 타입 안전한 DTO 자동 역직렬화.
  - `res.safe_headers`: 민감 헤더(`Authorization`, `Cookie` 등) 자동 마스킹.
- **다중 서비스 계층형 설정 로더 (Cascading Multi-Service Config)**:
  - `명시적 인자 (kwargs)` > `환경변수 (HTTP_* / COURIER_*)` > `YAML (courier.yaml)` > `JSON (courier.json)` > `기본값` 5단계 자동 병합.
  - 서비스별 독립 설정 및 싱글톤 클라이언트 자동 주입 (`http.get_client("payment")`).
- **지수 백오프 기반 스마트 자동 재시도 (Full Jitter Retry)**:
  - 일시적 장애(429, 500, 502, 503, 504) 및 네트워크 타임아웃 자동 재시도.
  - Thundering Herd를 방지하는 Full Jitter 공식 적용 및 HTTP `Retry-After` 헤더 자동 연동.
  - 비멱등 요청(POST, PATCH) 안전망(기본 재시도 차단) 내장.
- **동기 & 비동기 완벽 대칭 지원**:
  - 동기: `http.get()`, `http.post()`, `client.get()`
  - 비동기: `http.async_get()`, `http.async_post()`, `client.async_get()`
- **소켓 누수 0% (Zero Socket Leak)**:
  - `httpx.Limits` 기반 커넥션 풀링 및 `atexit` 프로세스 종료 훅 자동 등록.
  - 풀 초과 시 안전한 대기 큐 및 `pool_timeout` 안전망.
  - 1MB 초과 응답 메모리 보호(Truncation) 내장.
- **선언적 API 데코레이터**:
  - `@courier`, `@get`, `@post`를 통한 깔끔한 인터페이스 기반 API 레이어 분리.

---

## 📦 설치 (Installation)

```bash
pip install courier
```

---

## ⚙️ 설정 예제 (Configuration)

설정은 **`courier.yaml`**, **`courier.json`**, 또는 **환경변수**를 통해 계층형으로 관리할 수 있습니다.

### 1) 계층형 YAML (`courier.yaml`)
```yaml
# courier.yaml
http:
  default:
    timeout:
      connect: 3.0
      read: 10.0
      write: 5.0
      pool: 5.0
    retry:
      max_retries: 3
      backoff_factor: 0.5
      status_forcelist: [429, 500, 502, 503, 504]
    pool:
      max_connections: 100
      max_keepalive_connections: 20

  services:
    payment:
      base_url: "https://api.payment.com/v1"
      timeout:
        read: 5.0
      headers:
        Authorization: "Bearer secret-payment-key"
      retry:
        max_retries: 2
        retry_on_post: false

    notification:
      base_url: "https://api.notification.com"
      timeout:
        read: 3.0
```

### 2) 계층형 JSON (`courier.json`)
```json
{
  "http": {
    "default": {
      "timeout": { "read": 10.0 },
      "retry": { "max_retries": 3 }
    },
    "services": {
      "payment": {
        "base_url": "https://api.payment.com/v1",
        "headers": {
          "Authorization": "Bearer secret-payment-key"
        }
      }
    }
  }
}
```

### 3) 환경변수 (`.env` 또는 시스템 환경변수)
```bash
# 전역 기본 설정
export HTTP_TIMEOUT=10.0
export HTTP_MAX_RETRIES=3

# 특정 서비스별 오버라이드 (HTTP_CLIENT_{SERVICE}_{KEY})
export HTTP_CLIENT_PAYMENT_BASE_URL=https://api.payment.com/v1
export HTTP_CLIENT_PAYMENT_TIMEOUT=5.0
```

---

## 🚀 사용법 (Usage)

### 1. 기본 API 호출 및 Result 패턴 활용
```python
from courier import http

# 동기 GET 요청
res = http.get("https://jsonplaceholder.typicode.com/todos/1")

# 성공 여부 확인
if res.is_success:
    print("성공 데이터:", res.data)
    print("소요 시간(ms):", res.duration_ms)
else:
    print(f"실패 [{res.status_code}]:", res.error.message)

# Rust 스타일 unwrap: 실패 시 ApiCallError 예외 발생, 성공 시 데이터 반환
data = res.unwrap()
```

### 2. Pydantic v2 모델 자동 바인딩 (`res.into`)
```python
from pydantic import BaseModel
from courier import http

class TodoItem(BaseModel):
    id: int
    title: str
    completed: bool

res = http.get("https://jsonplaceholder.typicode.com/todos/1")

# Pydantic 모델로 타입 안전하게 자동 역직렬화
todo: TodoItem = res.into(TodoItem)
print(todo.title)
```

### 3. 다중 서비스 클라이언트 (`http.get_client`)
```python
from courier import http

# courier.yaml의 'payment' 설정이 자동 주입된 클라이언트 획득
payment_client = http.get_client("payment")

# base_url("https://api.payment.com/v1")이 자동 접두어로 붙음
res = payment_client.post("/charges", json={"amount": 50000, "currency": "KRW"})
```

### 4. 비동기(Async) 지원
```python
import asyncio
from courier import http

async def fetch_data():
    # 비동기 호출
    res = await http.async_get("https://jsonplaceholder.typicode.com/todos/1")
    return res.unwrap()

asyncio.run(fetch_data())
```

### 5. 선언적 API 데코레이터 (`@courier`)
```python
from courier import courier, get, post

@courier(base_url="https://jsonplaceholder.typicode.com")
class JsonPlaceholderClient:
    @get("/todos/{todo_id}")
    def get_todo(self, todo_id: int):
        ...

    @post("/todos")
    def create_todo(self, json: dict):
        ...

client = JsonPlaceholderClient()
res = client.get_todo(todo_id=1)
print(res.data)
```

---

## 🧪 테스트 실행 (Testing)

```bash
uv run pytest --cov=courier tests/
```

- **72개 테스트 100% Pass**
- **라인 커버리지 95% 달성**

---

## 📄 라이선스 (License)

MIT License.
