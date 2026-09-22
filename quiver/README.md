# quiver

> **Modern, Zero-Dependency, Fully Type-Safe Utility Toolkit for Python (Python 3.10+)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Zero-Dependency](https://img.shields.io/badge/dependencies-0%20(Pure%20Stdlib)-brightgreen.svg)](https://github.com/ozplayground/python-package)
[![Typing: PEP 561](https://img.shields.io/badge/typing-PEP%20561%20py.typed-blue.svg)](https://peps.python.org/pep-0561/)
[![Tests: 194 passed](https://img.shields.io/badge/tests-194%20passed-success.svg)](https://github.com/ozplayground/python-package)
[![Coverage: 99%](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com/ozplayground/python-package)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`quiver`는 파이썬 기본 표준 라이브러리(Stdlib)에 아쉬웠던 실무 킬러 유틸리티들을 모아, **필요할 때마다 언제든 즉시 활용할 수 있도록 5대 도메인으로 체계화한 순수 파이썬(Zero-Dependency) 모던 유틸리티 툴킷**입니다.

JavaScript의 Radash/Lodash, Kotlin의 Scope Functions, Java Guava의 CaseFormat/Stopwatch, Rust의 Itertools 설계 철학을 모던 파이썬 3.10+의 엄격한 타입 세이프티(PEP 612 `ParamSpec`, PEP 561 `py.typed`)와 결합하였습니다.

---

## ✨ 핵심 설계 철학 (Core Principles)

1. **Zero-Dependency (런타임 의존성 0개)**:
   - 외부 서드파티 패키지나 C-Extension 종속성이 전혀 없습니다 (`dependencies = []`).
   - 파이썬 3.10+ 내장 표준 라이브러리(C-Python 네이티브 엔진)만으로 작성되어, Docker 경량 빌드(Alpine 등) 및 폐쇄망 환경에서도 0.9ms 만에 즉시 설치됩니다.
2. **Python 3.10+ Strict Typing First**:
   - `py.typed` 마커 기본 내장. `mypy --strict` 및 `pyright` 환경에서 100% 무결점 정적 타입 추론을 보장합니다.
   - 데코레이터(`@retry`, `@memoize`, `@measure_time`)를 씌워도 원래 함수의 파라미터 시그니처와 반환 타입이 `ParamSpec`을 통해 온전히 보존됩니다.
3. **불변성(Immutability) & 순수 함수(Pure Functions)**:
   - 원본 컬렉션을 변경(In-place Mutation)하지 않고 Copy-on-Write (CoW) 패턴을 적용합니다.
   - 순환 참조(Circular Reference) 자동 감지 가드로 무한 루프 및 OOM 크래시를 원천 차단합니다.
4. **스레드 안전성(Thread-Safety) 기본 보장**:
   - 재귀 데드락을 방지하는 `threading.RLock` 기반 `memoize`, Double-Checked Locking `once`, 원자적 토큰 버킷 `RateLimiter` 완비.

---

## 📦 설치 (Installation)

```bash
pip install quiver
```

---

## 🏹 5대 핵심 모듈 (5 Pillars of Quiver)

### 1. `quiver.collections` (불변 컬렉션 연산)

배열과 딕셔너리를 다루는 번거로운 반복문과 인덱스 연산을 제거합니다.

```python
from quiver import (
    chunk, flatten, group_by, key_by, partition, 
    uniq_by, windowed, deep_get, deep_set, deep_merge, pick, omit, invert
)

# 1) 청크 분할 (Chunking) & 슬라이딩 윈도우 (Windowed)
list(chunk([1, 2, 3, 4, 5], size=2))           # [[1, 2], [3, 4], [5]]
list(windowed([1, 2, 3, 4], size=2, step=1))   # [(1, 2), (2, 3), (3, 4)]

# 2) 평탄화 (Flattening) - 순환 참조 방어 내장
flatten([[1, [2]], 3], depth=2)                # [1, 2, 3]

# 3) 조건 분할 (Partition)
evens, odds = partition([1, 2, 3, 4, 5], lambda x: x % 2 == 0)
# evens: [2, 4], odds: [1, 3, 5]

# 4) 그룹핑 & 키 매핑
users = [{"id": 1, "role": "admin"}, {"id": 2, "role": "user"}]
group_by(users, lambda u: u["role"])           # {"admin": [...], "user": [...]}
key_by(users, lambda u: u["id"])               # {1: {...}, 2: {...}}

# 5) 중복 제거 (Uniq By)
uniq_by([{"id": 1}, {"id": 1}, {"id": 2}], lambda x: x["id"])  # [{"id": 1}, {"id": 2}]

# 6) 중첩 딕셔너리 안전 탐색 및 갱신 (Deep Get / Deep Set / Deep Merge)
data = {"user": {"profile": {"name": "Alice"}}}
deep_get(data, "user.profile.name")            # "Alice"
deep_get(data, "user.unknown.age", default=20) # 20 (KeyError 방지)

updated = deep_set(data, "user.profile.age", 25) # 원본 data는 불변 유지!

# 7) 딕셔너리 키 선택 / 제외 (Pick & Omit)
pick({"a": 1, "b": 2, "c": 3}, "a", "c")       # {"a": 1, "c": 3}
omit({"a": 1, "b": 2, "c": 3}, "b")            # {"a": 1, "c": 3}
```

---

### 2. `quiver.behavior` (함수 합성 및 실행 제어)

함수의 합성, 재시도, 캐싱, 빈도 제어를 선언적으로 처리합니다.

```python
from quiver import pipe, compose, curry, once, debounce, throttle, memoize, retry

# 1) 파이프라이닝 (Pipe) & 함수 합성 (Compose)
result = pipe(5, lambda x: x * 2, lambda x: x + 1)  # (5 * 2) + 1 = 11
fn = compose(lambda x: x + 1, lambda x: x * 2)       # (x * 2) + 1
fn(5)  # 11

# 2) 커링 (Curry)
@curry
def add(a: int, b: int, c: int) -> int:
    return a + b + c

add(1)(2)(3)  # 6
add(1, 2)(3)  # 6

# 3) 1회만 실행 보장 (Once - Double-Checked Locking 스레드 안전)
@once
def initialize_system():
    print("시스템 1회 초기화")

# 4) TTL 및 LRU 지원 스레드 세이프 메모이제이션 (Memoize)
@memoize(ttl_seconds=60.0, maxsize=100)
def fetch_heavy_calculation(x: int) -> int:
    return x ** 2

# 5) 지수 백오프 + Full Jitter 스마트 재시도 (Retry)
@retry(max_attempts=3, backoff_base=0.5, backoff_max=10.0, exceptions=(IOError,))
def unstable_network_call():
    ...
```

---

### 3. `quiver.strings` (케이스 변환 및 문자열 보안)

다양한 네이밍 컨벤션 변환과 개인정보(PII) 마스킹을 제공합니다.

```python
from quiver import (
    to_camel_case, to_snake_case, to_kebab_case, to_pascal_case,
    slugify, truncate, mask_sensitive
)

# 1) 케이스 변환 (Case Conversions)
to_camel_case("user_first_name")      # "userFirstName"
to_snake_case("userFirstName")        # "user_first_name"
to_kebab_case("userFirstName")        # "user-first-name"
to_pascal_case("user_first_name")     # "UserFirstName"

# 2) URL 슬러그화 (Slugify - 유니코드/한글 지원)
slugify("Hello World! 2026")          # "hello-world-2026"
slugify("파이썬 유틸리티", allow_unicode=True)  # "파이썬-유틸리티"

# 3) 단어 경계 보존 자르기 (Truncate)
truncate("The quick brown fox jumps", length=15, preserve_words=True)
# "The quick..."

# 4) 민감 정보 마스킹 (Mask Sensitive)
mask_sensitive("user@example.com", mask_type="email")       # "u***r@example.com"
mask_sensitive("010-1234-5678", mask_type="phone")          # "010-****-5678"
mask_sensitive("900101-1234567", mask_type="rrn")           # "900101-1******"
mask_sensitive("1234-5678-9012-3456", mask_type="card")     # "1234-****-****-3456"
```

---

### 4. `quiver.scope` (Kotlin 스타일 스코프 함수)

임시 변수를 없애고 깔끔한 체이닝과 널 안전(Null-Safety) 코드를 작성합니다.

```python
from quiver import let, also, tap, take_if, take_unless, coalesce

# 1) let: None 안전 변환 (값이 None이면 람다를 실행하지 않고 None 반환)
user_id = let(fetch_user(), lambda u: u.id)

# 2) also / tap: 사이드 이펙트 실행 후 원래 객체 그대로 반환
config = also(load_config(), lambda c: print(f"Loaded: {c}"))

# 3) take_if / take_unless: 조건부 값 필터링
age = take_if(input_age, lambda a: a >= 18)  # 18세 미만이면 None 반환

# 4) coalesce: 첫 번째 None이 아닌 값 선택 (Falsy 0, "" 보존!)
timeout = coalesce(user_timeout, env_timeout, 30)
```

---

### 5. `quiver.timing` (고정밀 계측 및 속도 제한)

OS 단조 증가 시계 기반의 고정밀 계측과 토큰 버킷 속도 제한을 제공합니다.

```python
import time
from quiver import Stopwatch, measure_time, RateLimiter

# 1) 나노초 정밀 단조 시계 스톱워치 (Stopwatch)
with Stopwatch() as sw:
    time.sleep(0.05)
    sw.lap("step_1")
    time.sleep(0.05)

print(sw.elapsed_ms)    # 100.2 ms
print(sw.laps)          # [LapRecord(name='step_1', elapsed_ms=50.1, ...)]

# 2) 실행 시간 측정 데코레이터 / 컨텍스트 (Measure Time)
@measure_time(prefix="Database Query")
def run_query():
    ...

# 3) 원자적 토큰 버킷 레이트 리미터 (RateLimiter - 동기 & 비동기 지원)
limiter = RateLimiter(rate=10, per=1.0, burst=20)  # 초당 10개, 버스트 20개

# 동기 컨텍스트
with limiter:
    call_external_api()

# 비동기 컨텍스트
async def handle_request():
    async with limiter:
        await fetch_remote_data()
```

---

## 🧪 테스트 및 무결성 검증 (Testing)

```bash
uv run pytest --cov=quiver tests/
```

- **194개 유닛 및 멀티스레드 동시성 테스트 100% Pass** (1.0초)
- **전체 라인 커버리지 99% 달성**
- **100 스레드 동시성 스트레스 검증 완비 (`threading.Barrier(100)`)**

---

## 📄 라이선스 (License)

This project is licensed under the [MIT License](LICENSE).
