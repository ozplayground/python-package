# quiver

> Python 3.10+ 표준 라이브러리만으로 작성된 런타임 의존성 없는(Zero-Dependency) 타입 세이프 유틸리티 툴킷

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Zero-Dependency](https://img.shields.io/badge/dependencies-0%20(Pure%20Stdlib)-brightgreen.svg)](https://github.com/ozplayground/python-package)
[![Typing: PEP 561](https://img.shields.io/badge/typing-PEP%20561%20py.typed-blue.svg)](https://peps.python.org/pep-0561/)
[![Tests: 194 passed](https://img.shields.io/badge/tests-194%20passed-success.svg)](https://github.com/ozplayground/python-package)
[![Coverage: 99%](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com/ozplayground/python-package)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`quiver`는 일상적인 애플리케이션 개발 시 자주 마주치는 컬렉션 가공, 고차 함수 합성, 문자열 정규화, 실행 시간 계측 등의 작업을 표준 라이브러리 기반으로 깔끔하게 처리하기 위한 유틸리티 패키지입니다.

외부 서드파티 라이브러리(`dependencies = []`)나 C 확장 모듈을 일체 사용하지 않으며, 13.6KB 단일 휠 아카이브로 배포되어 설치 지연이나 의존성 충돌 없이 즉시 적용할 수 있습니다.

---

## 핵심 설계 특성

- **Zero-Dependency (런타임 의존성 0개)**: 외부 패키지를 설치하지 않으므로 빌드 파이프라인의 보안 감사(Audit) 부담을 줄이고 베이스 이미지를 가볍게 유지합니다.
- **정적 타입 지원 (PEP 561 & PEP 612)**: `quiver/py.typed` 마커와 `ParamSpec`을 포함하여 `mypy --strict` 및 `pyright` 환경에서 데코레이터 적용 후에도 원본 함수의 인자 타입과 반환 타입을 보존합니다.
- **불변성 기본 적용**: 컬렉션 연산 시 인플레이스 수정(In-place Mutation)을 지양하고 새 컨테이너를 반환하는 Copy-on-Write 방식을 채택합니다.
- **스레드 안전성**: `threading.RLock` 기반 메모이제이션과 원자적 토큰 버킷 속도 제한기를 제공하여 멀티스레드 환경에서도 안전하게 동작합니다.

---

## 설치 (Installation)

```bash
pip install quiver
# 또는 uv 사용 시
uv add quiver
```

13.6KB의 순수 파이썬 휠(`quiver-0.1.0-py3-none-any.whl`)로 배포되므로 별도의 C 컴파일러(GCC 등) 없이 1ms 내외로 설치가 완료됩니다.

---

## 주요 모듈 구성 및 사용 예시

### 1. `quiver.collections` (컬렉션 조작)

리스트 및 딕셔너리 데이터를 원본 훼손 없이 가공합니다. 순환 참조가 감지되면 무한 루프에 빠지지 않고 `ValueError`를 발생시킵니다.

```python
from quiver import (
    chunk, flatten, group_by, key_by, partition, 
    uniq_by, windowed, deep_get, deep_set, deep_merge, pick, omit, invert
)

# 청크 분할 및 슬라이딩 윈도우
list(chunk([1, 2, 3, 4, 5], size=2))           # [[1, 2], [3, 4], [5]]
list(windowed([1, 2, 3, 4], size=2, step=1))   # [(1, 2), (2, 3), (3, 4)]

# 다차원 리스트 평탄화 (depth 지정 가능, 순환 참조 감지 시 ValueError)
flatten([[1, [2]], 3], depth=2)                # [1, 2, 3]

# 조건에 따른 분할 (참/거짓 튜플 반환)
evens, odds = partition([1, 2, 3, 4, 5], lambda x: x % 2 == 0)
# evens: [2, 4], odds: [1, 3, 5]

# 그룹핑 및 키 매핑
users = [{"id": 1, "role": "admin"}, {"id": 2, "role": "user"}]
group_by(users, lambda u: u["role"])           # {"admin": [...], "user": [...]}
key_by(users, lambda u: u["id"])               # {1: {...}, 2: {...}}

# 키 기반 중복 제거 (순서 보존)
uniq_by([{"id": 1}, {"id": 1}, {"id": 2}], lambda x: x["id"])  # [{"id": 1}, {"id": 2}]

# 중첩 딕셔너리 점(.) 경로 접근 및 안전 갱신
data = {"user": {"profile": {"name": "Alice"}}}
deep_get(data, "user.profile.name")            # "Alice"
deep_get(data, "user.unknown.age", default=20) # 20

# deep_set은 원본 data를 수정하지 않고 새 딕셔너리를 반환합니다.
updated = deep_set(data, "user.profile.age", 25)

# 키 선택 및 제외
pick({"a": 1, "b": 2, "c": 3}, "a", "c")       # {"a": 1, "c": 3}
omit({"a": 1, "b": 2, "c": 3}, "b")            # {"a": 1, "c": 3}
```

---

### 2. `quiver.behavior` (함수 합성 및 실행 제어)

함수의 합성, 재시도, 캐싱, 호출 빈도 제어를 처리합니다.

```python
from quiver import pipe, compose, curry, once, debounce, throttle, memoize, retry

# 파이프라인 및 함수 합성
result = pipe(5, lambda x: x * 2, lambda x: x + 1)  # (5 * 2) + 1 = 11
fn = compose(lambda x: x + 1, lambda x: x * 2)       # (x * 2) + 1
fn(5)  # 11

# 커링
@curry
def add(a: int, b: int, c: int) -> int:
    return a + b + c

add(1)(2)(3)  # 6
add(1, 2)(3)  # 6

# 단 1회 실행 보장 (Double-Checked Locking 적용)
@once
def initialize_system():
    # 여러 스레드가 동시에 접근해도 1회만 실행됩니다.
    setup_logging()

# TTL 및 LRU 용량 제한 캐싱 (스레드 안전)
@memoize(ttl_seconds=60.0, maxsize=100)
def fetch_user_profile(user_id: int) -> dict:
    return query_db(user_id)

# Full Jitter 지수 백오프 기반 재시도
@retry(max_attempts=3, backoff_base=0.5, backoff_max=10.0, exceptions=(IOError,))
def fetch_remote_resource():
    return request_upstream()
```

---

### 3. `quiver.strings` (문자열 정규화 및 마스킹)

식별자 케이스 변환 및 개인정보(PII) 로그 마스킹 유틸리티입니다. 사전 컴파일된 정규식을 사용하여 입력 길이에 비례하는 $O(N)$ 시간 내에 동작합니다.

```python
from quiver import (
    to_camel_case, to_snake_case, to_kebab_case, to_pascal_case,
    slugify, truncate, mask_sensitive
)

# 케이스 변환
to_camel_case("user_first_name")      # "userFirstName"
to_snake_case("userFirstName")        # "user_first_name"
to_kebab_case("userFirstName")        # "user-first-name"
to_pascal_case("user_first_name")     # "UserFirstName"

# URL 슬러그 생성 (한글 유니코드 지원)
slugify("Python Packaging 2026")              # "python-packaging-2026"
slugify("파이썬 패키지 가이드", allow_unicode=True)  # "파이썬-패키지-가이드"

# 단어 경계 보존 자르기
truncate("The quick brown fox jumps", length=15, preserve_words=True)
# "The quick..."

# 민감 정보 마스킹 (이메일, 전화번호, 주민등록번호, 카드번호)
mask_sensitive("developer@example.com", mask_type="email")  # "d***r@example.com"
mask_sensitive("010-1234-5678", mask_type="phone")         # "010-****-5678"
mask_sensitive("900101-1234567", mask_type="rrn")          # "900101-1******"
mask_sensitive("1234-5678-9012-3456", mask_type="card")    # "1234-****-****-3456"
```

---

### 4. `quiver.scope` (스코프 함수 및 널 안전)

중간 임시 변수를 줄이고 표현식 위주의 흐름을 구성할 때 유용합니다.

```python
from quiver import let, also, tap, take_if, take_unless, coalesce

# None 안전 값 변환 (대상 객체가 None이면 변환 함수를 호출하지 않고 None 반환)
user_id = let(find_user(), lambda u: u.id)

# 사이드 이펙트 실행 후 원래 객체 반환 (로깅, 디버깅)
user = also(create_user(), lambda u: audit_log(u.id))

# 조건부 필터링 (조건 불만족 시 None 반환)
valid_age = take_if(input_age, lambda a: a >= 18)

# 첫 번째 None이 아닌 값 선택 (0, False, "" 등의 Falsy 값을 보존)
timeout = coalesce(custom_timeout, config_timeout, 30)
```

---

### 5. `quiver.timing` (단조 시계 계측 및 속도 제한)

운영체제의 단조 증가 시계(`time.perf_counter_ns`)를 사용하여 시스템 시계 변경(NTP 동기화 등)에 영향을 받지 않는 계측을 제공합니다.

```python
import time
from quiver import Stopwatch, measure_time, RateLimiter

# 나노초 단위 정밀 스톱워치
with Stopwatch() as sw:
    time.sleep(0.05)
    sw.lap("db_query")
    time.sleep(0.05)

print(sw.elapsed_seconds)  # 0.1002...
print(sw.laps)             # [LapRecord(name='db_query', lap_seconds=0.0501, ...)]

# 함수 실행 시간 계측 데코레이터
@measure_time(prefix="Task execution")
def process_batch():
    ...

# 토큰 버킷 속도 제한기 (동기/비동기 지원, 스레드 안전)
limiter = RateLimiter(rate=10, per=1.0, burst=20)  # 초당 10개, 버스트 최대 20개

# 동기 컨텍스트
with limiter:
    call_external_api()

# 비동기 컨텍스트
async def handle_async_request():
    async with limiter:
        await fetch_remote_data()
```

---

## 트레이드오프 및 사용 시 주의사항 (Gotchas)

- **인메모리 캐시 및 속도 제한**: `memoize`와 `RateLimiter`는 단일 프로세스 메모리 내에서 동작합니다. 멀티 프로세스 워커(예: Gunicorn, Celery) 간에 캐시나 처리율 제한을 공유해야 하는 경우에는 Redis 등 외부 분산 저장소를 사용하는 것이 적절합니다.
- **Copy-on-Write 메모리 오버헤드**: `deep_set` 및 `deep_merge`는 원본 데이터를 수정하지 않고 복사본을 생성합니다. 수십만 개 이상의 요소를 가진 매우 큰 딕셔너리를 빈번하게 부분 갱신할 때는 객체 생성에 따른 메모리 사용량을 고려해야 합니다.
- **Debounce / Throttle의 프로세스 종료**: `debounce`와 `throttle`은 백그라운드 타이머(`threading.Timer`)를 생성합니다. 애플리케이션 종료 시 잔여 타이머가 즉시 중단되도록 인스턴스의 `cancel()` 메서드를 적절히 호출해 주는 것을 권장합니다.

---

## 테스트 및 검증 현황

```bash
uv run pytest --cov=quiver tests/
```

- **194개 유닛 및 멀티스레드 동시성 테스트 통과** (소요 시간: 0.97초)
- **전체 라인 커버리지**: **99%**
- **동시성 검증**: `threading.Barrier(100)` 기반 100개 스레드 동시 진입 스트레스 테스트 통과

---

## 라이선스

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다.
