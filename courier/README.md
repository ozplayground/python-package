# courier

> **Production HTTP Client & Connection Pool Manager for Python (HTTPX & Pydantic v2)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![HTTPX](https://img.shields.io/badge/httpx-0.28+-orange.svg)](https://www.encode.io/httpx/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-green.svg)](https://docs.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`courier`는 마이크로서비스 환경에서 외부 HTTP API를 연동할 때 발생하는 커넥션 풀링, 4단 타임아웃, 지수 백오프 재시도, 응답 DTO 역직렬화 보일러플레이트를 단순화하는 HTTP 클라이언트 라이브러리입니다.

네트워크 장애나 4xx/5xx 에러 상황에서도 애플리케이션 프로세스가 예기치 않게 크래시되지 않도록 Result 패턴 기반의 통일된 `ApiResponse[T]`를 반환하며, 프로세스 종료 시 커넥션 풀을 안전하게 닫아 파일 디스크립터(FD) 누수를 방지합니다.

---

## 🛠️ 핵심 기능

- **Result 패턴 기반 응답 모델 (`ApiResponse[T]`)**:
  - 상태 코드와 관계없이 항상 구조화된 응답 객체를 반환하여 호출 측 예외 처리 로직을 단순화합니다.
  - `res.unwrap()`: 성공 응답(`2xx`) 시 페이로드를 반환하고, 실패 시 세부 정보가 담긴 `ApiCallError`를 발생시킵니다.
  - `res.into(Model)`: 응답 데이터를 Pydantic v2 모델로 직접 역직렬화합니다.
  - `res.safe_headers`: 로그 출력 시 `Authorization`, `Cookie` 등 민감 헤더를 자동 마스킹합니다.
- **5단계 계층형 설정 로더 (Cascading Config)**:
  - `명시적 인자 (kwargs)` > `환경변수 (HTTP_CLIENT_*)` > `YAML (courier.yaml)` > `JSON (courier.json)` > `기본값` 순서로 병합됩니다.
  - 서비스별로 독립된 베이스 URL, 타임아웃, 커넥션 풀을 구성하고 `http.get_client("payment")` 형태로 주입받아 사용합니다.
- **Thundering Herd 방지 지수 백오프 & Full Jitter**:
  - 일시적인 5xx(502, 503, 504) 및 429(Too Many Requests), 연결 타임아웃 발생 시 자동 재시도합니다.
  - AWS 권장 Full Jitter 알고리즘을 적용하여 장애 복구 시 트래픽 폭주를 분산하며, `Retry-After` 헤더 수치를 우선 적용합니다.
  - 멱등성이 보장되지 않는 `POST` 요청은 기본적으로 재시도 대상에서 제외합니다 (`retry_on_post=False`).
- **소켓 파일 디스크립터(FD) 누수 방지**:
  - `httpx.Limits` 커넥션 풀 관리와 `atexit` 훅을 통해 파이썬 프로세스 종료 시 유휴 소켓을 안전하게 회수합니다.
  - FastAPI/Starlette 환경에서는 ASGI Lifespan 컨텍스트를 통한 명시적 비동기 풀 종료(`await http.aclose_all()`)를 지원합니다.
- **선언적 클라이언트 데코레이터**:
  - `@courier`, `@get`, `@post` 데코레이터로 API 스펙 인터페이스를 명확하게 분리하여 작성할 수 있습니다.

---

## 📦 설치

```bash
pip install courier
```

---

## ⚙️ 설정 가이드

설정은 환경변수, `courier.yaml`, 또는 `courier.json` 파일로 관리할 수 있습니다. 설정 파일의 최상위 키는 서비스 이름(`default`, `payment`, `crawler` 등)입니다.

### 1) YAML 설정 (`courier.yaml`)
```yaml
# courier.yaml: 프로젝트 루트 또는 config/ 디렉토리에 위치
default:
  base_url: "https://api.internal.service.local"
  timeout: 10.0
  connect_timeout: 3.0
  read_timeout: 10.0
  write_timeout: 10.0
  pool_timeout: 5.0
  pool_size: 20
  max_keepalive: 10
  keepalive_expiry: 30.0
  retry:
    max_retries: 3
    backoff_factor: 0.5
    max_backoff_seconds: 30.0
    retry_on_post: false

payment:
  base_url: "https://api.payment.internal/v1"
  timeout: 5.0
  connect_timeout: 2.0
  read_timeout: 5.0
  pool_size: 30
  retry:
    max_retries: 2
    retry_on_post: false
```

### 2) 환경변수 설정 (`.env` 또는 컨테이너 주입)
환경변수 접두사는 `HTTP_CLIENT_{SERVICE_NAME}_{PROPERTY}` 형식을 따릅니다:
```bash
# 기본 클라이언트 설정
export HTTP_CLIENT_DEFAULT_BASE_URL=https://api.internal.service.local
export HTTP_CLIENT_DEFAULT_TIMEOUT=10.0
export HTTP_CLIENT_DEFAULT_POOL_SIZE=20

# 특정 서비스 오버라이드 (예: payment 서비스)
export HTTP_CLIENT_PAYMENT_BASE_URL=https://api.payment.internal/v1
export HTTP_CLIENT_PAYMENT_TIMEOUT=5.0
export HTTP_CLIENT_PAYMENT_POOL_SIZE=30
export HTTP_CLIENT_PAYMENT_RETRY_RETRY_ON_POST=false
```

---

## 🚀 실무 사용 예제

### 1. 기본 호출 및 Result 패턴 활용
```python
from courier import http

# 동기 요청 (전역 싱글톤 http 프록시 사용)
res = http.get("https://api.example.com/items/42")

if res.is_success:
    print(f"조회 성공 (소요 시간: {res.duration_ms}ms):", res.data)
else:
    # 4xx, 5xx 에러 또는 네트워크 단절 시에도 예외로 터지지 않고 error 객체에 담김
    print(f"조회 실패 [{res.status_code}]:", res.error.message)

# unwrap: 성공 시 데이터 반환, 실패 시 구체적인 ApiCallError 발생
data = res.unwrap()
```

### 2. Pydantic v2 모델 역직렬화 (`res.into`)
```python
from pydantic import BaseModel
from courier import http

class UserProfile(BaseModel):
    id: int
    name: str
    email: str

res = http.get("https://api.example.com/users/1")

# Pydantic v2 모델로 직접 파싱 및 타입 힌트 지원
user: UserProfile = res.into(UserProfile)
print(user.name, user.email)
```

### 3. 서비스별 독립 클라이언트 (`http.get_client`)
```python
from courier import http

# courier.yaml 또는 환경변수의 'payment' 설정이 바인딩된 인스턴스 반환
payment_client = http.get_client("payment")

# base_url이 자동으로 결합되어 /charges 엔드포인트로 전송
res = payment_client.post("/charges", json={"amount": 15000, "currency": "KRW"})
```

### 4. FastAPI Lifespan 연동 (비동기 소켓 회수)
컨테이너 환경에서 롤링 배포(Rolling Update)나 SIGTERM 수신 시 열려 있는 HTTP 커넥션 풀을 안전하게 회수합니다:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from courier import http

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 기동
    yield
    # 프로세스 종료 단계: 이벤트 루프가 닫히기 전에 열린 소켓 풀 회수
    await http.aclose_all()

app = FastAPI(lifespan=lifespan)

@app.get("/external-status")
async def check_status():
    res = await http.async_get("https://status.provider.com/health")
    return {"status": res.status_code, "ok": res.is_success}
```

### 5. 선언적 API 인터페이스 (`@courier`)
```python
from courier import courier, get, post

@courier(base_url="https://api.example.com")
class OrderGateway:
    @get("/orders/{order_id}")
    def get_order(self, order_id: str):
        ...

    @post("/orders")
    def create_order(self, json: dict):
        ...

gateway = OrderGateway()
res = gateway.get_order(order_id="ORD-2026-001")
```

---

## 🧪 테스트 실행

```bash
uv run pytest --cov=courier tests/
```

- 테스트 스위트: 동기/비동기 호출, 계층형 설정 병합, 지수 백오프, 동시성 커넥션 풀 검증 완료.

---

## 📄 라이선스

MIT License.
