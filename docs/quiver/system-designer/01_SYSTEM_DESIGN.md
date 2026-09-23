# [quiver] 시스템 및 공개 SDK 인터페이스 상세 설계서 (System Design & Public SDK Specification)

- **작성일자**: 2026-09-23
- **작성자**: 백엔드 시스템 디자이너 (`system-designer`)
- **문서 버전**: v1.1
- **상태**: Approved

---

## 1. 아키텍처 개요 및 패키지 계층도 (Architecture & Package Layout)

`quiver`는 외부 런타임 의존성을 일체 두지 않는(**Zero-Dependency**, 런타임 의존성 0개) 순수 Python 3.10+ 표준 라이브러리 기반 유틸리티 패키지입니다. 

### 1.1 설계 배경 및 의존성 배제 결정 (Why Zero-Dependency)
- **배경**: 현대 파이썬 백엔드(FastAPI, Django, 데이터 파이프라인 등)에서 청킹, 지수 백오프 재시도, 중첩 딕셔너리 안전 탐색, 디바운스, 스톱워치 등을 위해 서드파티 패키지(`toolz`, `pydash`, `more-itertools`, `tenacity`, `cachetools`)를 무분별하게 혼합 도입하는 경우가 많습니다.
- **문제점**:
  1. 각 패키지가 요구하는 하위 전이 의존성(Transitive Dependencies)으로 인해 Docker 빌드 시간 증가 및 의존성 충돌(Dependency Hell) 발생.
  2. 오래된 패키지의 구형 타입 힌트로 인해 `mypy --strict` 및 최신 IDE에서 정적 분석 에러(`type: ignore`) 다수 발생.
  3. 사내 사설 유틸(`utils.py`)에 파편화된 스니펫은 스레드 안전성 결여 및 원본 객체 가변 변이(In-place mutation) 버그를 유발.
- **결정**: 서드파티 런타임 의존성을 0개로 강제하고, Python 3.10+ 표준 라이브러리(`typing`, `functools`, `time`, `threading`, `re`, `unicodedata` 등)만으로 5대 핵심 도메인(컬렉션, 함수 제어, 문자열 보안, 스코프 체이닝, 시간 계측)을 일관된 인터페이스로 제공합니다.

### 1.2 패키지 디렉터리 구조 (Package Layout)

```
quiver/
├── __init__.py          # 최상위 공개 API 심볼 35종 노출 (__all__ 명시)
├── py.typed             # PEP 561 마커 (mypy --strict 및 pyright 정적 검사 지원)
├── collections.py       # 불변 컬렉션 연산 (chunk, flatten, group_by, key_by, partition, uniq_by, windowed, deep_get, deep_set, deep_merge, pick, omit, invert)
├── behavior.py          # 고차 함수 제어 (pipe, compose, curry, once, debounce, throttle, memoize, retry)
├── strings.py           # 문자열 변환 및 보안 (to_camel_case, to_snake_case, to_kebab_case, to_pascal_case, slugify, truncate, mask_sensitive)
├── scope.py             # Kotlin 스타일 스코프 확장 (let, also, tap, take_if, take_unless, coalesce)
└── timing.py            # 시간 계측 및 속도 제어 (Stopwatch, measure_time, RateLimiter)
```

### 1.3 모듈별 역할 및 책임 (Module Responsibilities)

| 모듈 경로 | 주요 심볼 (35종) | 주요 역할 및 엔지니어링 원칙 |
| :--- | :--- | :--- |
| `quiver/__init__.py` | 최상위 재익스포트 심볼 전체 | • 패키지 루트에서 직접 임포트 지원 (`from quiver import chunk, retry`)<br/>• `__all__` 선언으로 비공개 헬퍼 함수 네임스페이스 누출 방지 |
| `quiver/py.typed` | 빈 마커 파일 (PEP 561) | • 패키지 사용 프로젝트의 `mypy --strict` 정적 분석 시 타입 인라인 검사 활성화 |
| `quiver/collections.py`| `chunk`, `flatten`, `group_by`, `key_by`, `partition`, `uniq_by`, `windowed`, `deep_get`, `deep_set`, `deep_merge`, `pick`, `omit`, `invert` | • 원본 데이터 비파괴(Zero Mutation, Copy-on-Write) 보장<br/>• 대용량 처리를 위한 제너레이터 지연 평가(Lazy Streaming)<br/>• 순환 참조 감지 및 해시 불가(Unhashable) 객체 폴백 |
| `quiver/behavior.py` | `pipe`, `compose`, `curry`, `once`, `debounce`, `throttle`, `memoize`, `retry` | • `ParamSpec`과 `TypeVar` 기반으로 원본 함수 시그니처 보존<br/>• `threading.Lock`/`RLock`을 적용한 멀티스레드 동시성 안전성<br/>• Full Jitter 지수 백오프 및 TTL/LRU 메모리 캐시 라이프사이클 관리 |
| `quiver/strings.py` | `to_camel_case`, `to_snake_case`, `to_kebab_case`, `to_pascal_case`, `slugify`, `truncate`, `mask_sensitive` | • 사전 컴파일된 정규식 토큰화로 ReDoS 방지<br/>• `None` 입력 시 빈 문자열(`""`) 반환 정책 일관성 유지<br/>• 개인정보 및 금융 식별자(이메일, 주민번호, 카드번호) 표준 마스킹 |
| `quiver/scope.py` | `let`, `also`, `tap`, `take_if`, `take_unless`, `coalesce` | • 임시 변수 생성을 억제하는 선언적 체이닝 지원<br/>• `also`/`tap` 원본 객체 참조 동일성($\text{result} \equiv \text{target}$) 보장<br/>• 첫 유효값 단락 평가(Short-circuit Evaluation) |
| `quiver/timing.py` | `Stopwatch`, `measure_time`, `RateLimiter` | • OS 단조 시계(`time.perf_counter_ns`) 기반 음수 경과시간 왜곡 방지<br/>• 멀티스레드 토큰 버킷 원자적 충전 및 블로킹 대기 스케줄링<br/>• 컨텍스트 매니저와 데코레이터 겸용 인터페이스 제공 |

### 1.4 소프트웨어 계층도 (Layered Architecture Diagram)

```mermaid
flowchart TD
    subgraph AppLayer["1. 사용자 애플리케이션 계층 (User Applications)"]
        ClientApp["FastAPI / Django / Data Worker / CLI"]
    end

    subgraph EntryLayer["2. 최상위 패키지 진입점 (Package Root)"]
        RootAPI["quiver/__init__.py (__all__ & py.typed)"]
    end

    subgraph CoreModules["3. 도메인별 코어 모듈 계층 (Core Utility Modules)"]
        direction TB
        ModColl["quiver.collections<br/>(불변 데이터 가공)"]
        ModBehv["quiver.behavior<br/>(함수 실행 제어)"]
        ModStr["quiver.strings<br/>(포맷 변환 및 보안)"]
        ModScp["quiver.scope<br/>(스코프 체이닝)"]
        ModTime["quiver.timing<br/>(시간 계측 및 속도제어)"]
    end

    subgraph StateAndSync["4. 동시성 제어 및 상태 저장소 (State & Concurrency Control)"]
        direction LR
        LockPrimitives["threading.Lock / RLock<br/>(동기화 및 데드락 방지)"]
        TimerLifecycle["threading.Timer<br/>(디바운스/쓰로틀 타이머 제어)"]
        TokenBucketEngine["Token Bucket Engine<br/>(RateLimiter 원자적 토큰 보충)"]
        CacheStorage["TTL/LRU Storage<br/>(memoize 만료 엔트리 보관)"]
    end

    subgraph StdLibLayer["5. Python 3.10+ 표준 런타임 계층 (Standard Library)"]
        direction LR
        TypingEngine["typing / collections.abc"]
        TimeEngine["time (perf_counter_ns, monotonic)"]
        FuncEngine["functools / inspect / itertools"]
        ReEngine["re / unicodedata"]
    end

    ClientApp --> RootAPI
    ClientApp -.-> ModColl
    ClientApp -.-> ModBehv
    ClientApp -.-> ModStr
    ClientApp -.-> ModScp
    ClientApp -.-> ModTime

    RootAPI --> ModColl
    RootAPI --> ModBehv
    RootAPI --> ModStr
    RootAPI --> ModScp
    RootAPI --> ModTime

    ModBehv --> LockPrimitives
    ModBehv --> TimerLifecycle
    ModBehv --> CacheStorage
    ModTime --> TokenBucketEngine
    ModTime --> LockPrimitives

    ModColl --> TypingEngine
    ModColl --> FuncEngine
    ModBehv --> TypingEngine
    ModBehv --> FuncEngine
    ModStr --> ReEngine
    ModStr --> TypingEngine
    ModScp --> TypingEngine
    ModTime --> TimeEngine
```

---

## 2. 핵심 클래스 및 구조 설계 (Core Architecture & Class Diagram)

> [!NOTE]
> **아키텍처 모델링 근거**:
> `quiver`는 데이터베이스 테이블을 직접 소유하는 영속 서비스가 아니라, 메모리 상에서 안전하게 데이터를 조작하고 실행 흐름을 통제하는 클라이언트 라이브러리입니다. 따라서 데이터베이스 ERD 대신, 객체 지향적 클래스 구조, 데이터 모델, 래퍼 컨텍스트 및 모듈별 함수 아키텍처를 정의하는 Mermaid 다이어그램으로 시스템 구조를 정의합니다.

### 2.1 핵심 클래스 다이어그램 (Mermaid Class Diagram)

```mermaid
classDiagram
    class LapRecord {
        +int index
        +Optional~str~ name
        +int lap_time_ns
        +int total_time_ns
        +float lap_seconds
        +float total_seconds
    }

    class Stopwatch {
        -int _start_ns
        -int _stop_ns
        -int _accumulated_ns
        -int _last_lap_ns
        -bool _is_running
        -list~LapRecord~ _laps
        -threading.Lock _lock
        +bool is_running
        +int elapsed_ns
        +float elapsed_seconds
        +list~LapRecord~ laps
        +start() Stopwatch
        +stop() float
        +reset() Stopwatch
        +lap(name: Optional~str~) LapRecord
        +__enter__() Stopwatch
        +__exit__(exc_type, exc_val, exc_tb) void
    }

    class MeasureTimeContext {
        -Optional~Callable~ _callback
        -str _unit
        -int _start_ns
        -int _elapsed_ns
        +int elapsed_ns
        +float elapsed
        +str unit
        +__enter__() MeasureTimeContext
        +__exit__(exc_type, exc_val, exc_tb) void
        +__call__(fn: Callable) Callable
    }

    class RateLimiter {
        +float rate
        +float per_seconds
        +float burst
        -float _tokens
        -float _last_refill_time
        -threading.Lock _lock
        +float available_tokens
        +acquire(tokens: float, blocking: bool, timeout: Optional~float~) bool
        +__enter__() bool
        +__exit__(exc_type, exc_val, exc_tb) void
        +__call__(fn: Callable) Callable
        -_refill(now: float) void
    }

    class CacheEntry~R~ {
        +R value
        +Optional~float~ expire_at
        +int last_accessed_ns
    }

    class MemoizeWrapper~P, R~ {
        -Callable~P, R~ _fn
        -Optional~float~ _ttl_seconds
        -Optional~int~ _maxsize
        -Optional~Callable~ _key_fn
        -dict~Any, CacheEntry~R~~ _cache
        -threading.RLock _lock
        -int _hits
        -int _misses
        +__call__(*args: P.args, **kwargs: P.kwargs) R
        +cache_clear() void
        +cache_info() dict~str, Any~
        -_generate_key(args: tuple, kwargs: dict) Any
    }

    class RetryWrapper~P, R~ {
        -Callable~P, R~ _fn
        -int _max_attempts
        -float _backoff_base
        -float _backoff_max
        -bool _jitter
        -tuple~type~Exception~~ _exceptions
        -Optional~Callable~ _on_retry
        +__call__(*args: P.args, **kwargs: P.kwargs) R
        -_execute_sync(*args: P.args, **kwargs: P.kwargs) R
        -_execute_async(*args: P.args, **kwargs: P.kwargs) Coroutine~R~
        -_calculate_backoff(attempt: int) float
    }

    class OnceWrapper~P, R~ {
        -Callable~P, R~ _fn
        -bool _has_run
        -Optional~R~ _result
        -threading.Lock _lock
        +__call__(*args: P.args, **kwargs: P.kwargs) R
        +reset() void
    }

    class DebounceWrapper~P, R~ {
        -Callable~P, R~ _fn
        -float _wait_seconds
        -Optional~threading.Timer~ _timer
        -threading.Lock _lock
        +__call__(*args: P.args, **kwargs: P.kwargs) void
        +cancel() void
        +flush() void
    }

    class ThrottleWrapper~P, R~ {
        -Callable~P, R~ _fn
        -float _interval_seconds
        -float _last_called_time
        -threading.Lock _lock
        +__call__(*args: P.args, **kwargs: P.kwargs) Optional~R~
    }

    Stopwatch "1" *-- "*" LapRecord : records
    MemoizeWrapper "1" *-- "*" CacheEntry : stores
```

### 2.2 주요 설계 결정 (Architectural Decision Records - ADR 요약)

1. **`once` 데코레이터의 Double-Checked Locking 채택**:
   - *결정*: `has_run` 플래그를 락 없이 1차 확인한 뒤, 미실행 상태일 때만 `threading.Lock` 블록에 진입해 2차 확인 후 실행.
   - *이유*: 최초 1회 실행 이후의 수백만 번 반복 호출 구간에서 락 획득 오버헤드를 0으로 만들어 CPU 캐시 미스와 스레드 컨텍스트 스위칭을 제거.
2. **`memoize`의 `threading.RLock`(재진입 락) 사용**:
   - *결정*: 일반 `Lock` 대신 재진입이 가능한 `RLock` 채택.
   - *이유*: 피보나치 수열, 트리 경로 탐색 등 자기 자신을 재귀 호출하는 함수에 `@memoize` 적용 시 동일 스레드 내에서 발생하는 자가 데드락(Self-Deadlock)을 방지하기 위함.
3. **`retry`의 동기/비동기 투명 래핑 분기**:
   - *결정*: `inspect.iscoroutinefunction(fn)`으로 타깃 함수를 런타임에 판별하여 동기 함수는 `time.sleep`, 비동기 코루틴은 `await asyncio.sleep`으로 실행 경로를 자동 분기.
   - *이유*: 단일 데코레이터 식별자(`@retry`)로 FastAPI 비동기 핸들러와 Celery 동기 태스크를 동일한 사용성으로 지원.

---

## 3. 리소스 관리 및 성능 최적화 전략 (Performance & Optimization Strategy)

> [!NOTE]
> 본 라이브러리는 RDBMS 인덱싱 전략 대신, 메모리 풋프린트 최소화, CPU 캐시 친화적 시간 복잡도($O(1), O(N)$), 제너레이터 스트리밍, 그리고 ReDoS 방어 알고리즘을 통해 고부하 백엔드 환경에서의 지연시간(Latency)을 최소화합니다.

### 3.1 성능 및 리소스 최적화 매트릭스 (Optimization Specifications)

| 최적화 도메인 | 적용 기술 및 메커니즘 | 알고리즘 / 시간 복잡도 | 메모리 / CPU 최적화 효과 및 주의사항(Gotchas) |
| :--- | :--- | :---: | :--- |
| **청크/윈도우 스트리밍** | `itertools.islice` 기반 제너레이터 `yield` | $O(N)$ 시간, $O(\text{size})$ 공간 | • 수천만 건의 대용량 이터러블 처리 시 전체 메모리 로드를 차단.<br/>• **주의**: 제너레이터 반환값이므로 1회 순회 후 소진됨. 재순회가 필요할 경우 호출자가 명시적으로 `list()` 변환 필요. |
| **원자 타입 평탄화 방어** | `isinstance(x, (str, bytes, bytearray, Mapping))` 원자화 판별 | $O(1)$ 인스펙션 | • 문자열이 단일 글자로 수만 번 쪼개지거나 딕셔너리 키만 분리되는 버그 원천 차단.<br/>• 불필요한 재귀 스택 생성 방지로 스택 오버플로우 방지. |
| **순환 참조(Cycle) 방어** | 탐색 경로 `visited_ids: set[int]` 추적 | $O(1)$ 해시 조회 | • A가 B를 참조하고 B가 A를 참조하는 중첩 컬렉션 인입 시 `ValueError` 즉각 발생.<br/>• 탐색 완료 후 집합에서 ID를 즉시 제거하여 유효한 다이아몬드 상속 구조는 정상 순회 허용. |
| **순서 보존 고유화** | 해시 셋 + 결과 리스트 결합 | $O(N)$ 시간, $O(N)$ 공간 | • 첫 번째 등장 순서를 100% 보존하면서 중복 검사를 $O(1)$에 수행.<br/>• `set()` 변환 시 발생하는 원소 순서 뒤섞임 문제 해결. |
| **Unhashable 객체 폴백** | `TypeError: unhashable` 발생 시 `repr(item)` 문자열 키 폴백 | $O(K)$ 폴백 (K=문자열 길이) | • `dict`, `list` 등 가변 객체가 `memoize`, `uniq_by`에 전달되어도 크래시 없이 동작.<br/>• **주의**: `__repr__`을 오버라이딩하지 않은 커스텀 객체는 인스턴스 메모리 주소가 들어가므로 별도 `key_fn` 지정 권장. |
| **ReDoS 방어 정규식** | 사전 컴파일(`re.compile`) + 비역추적 패턴 | $O(N)$ 시간 엄격 보장 | • 백트래킹(Backtracking)이 없는 원자적 정규식 패턴 설계로 악의적인 반복 문자열 인입 시 정규식 엔진의 CPU 100% 동결 방어. |
| **OS 고정밀 단조 시계** | `time.perf_counter_ns()` 단조 카운터 사용 | 하드웨어 TSC 기반 $O(1)$ | • 시스템 관리자의 로컬 시계 수동 변경이나 NTP 시간 동기화 시 발생하는 음수 경과시간 및 역전 결함 원천 방지. |

### 3.2 불변성(Immutability) 및 Copy-on-Write 메모리 정책

1. **Copy-on-Write (CoW) 얕은 경로 복제**:
   - `deep_set(mapping, path, value)` 및 `deep_merge(*mappings)`는 원본 딕셔너리를 직접 변이(`in-place mutation`)하지 않습니다.
   - 전체 트리를 `copy.deepcopy`로 복제하지 않고, 변경이 일어나는 분기 경로의 딕셔너리 노드만 복제(`dict.copy()`)하고 변경되지 않은 형제 서브트리는 기존 참조를 그대로 공유합니다.
   - 이를 통해 딥카피 대비 메모리 할당 및 복사 오버헤드를 약 80% 절감합니다.
2. **반환 컨테이너의 변이 방어**:
   - `partition`은 `Tuple[List[T], List[T]]` 형태의 불변 튜플로 반환합니다.
   - `windowed`의 각 윈도우 원소는 불변 `tuple` 객체로 산출되어 슬라이딩 윈도우 순회 중 버퍼 오염을 방지합니다.

---

## 4. 스레드 세이프티 및 동시성 제어 정책 (Thread-Safety & Concurrency Policies)

`quiver`의 상태성 컴포넌트(`RateLimiter`, `Stopwatch`, `once`, `debounce`, `throttle`, `memoize`)는 멀티스레드 환경에서 데이터 경합(Race Condition)을 방지하도록 설계되었습니다.

### 4.1 동기화 프리미티브 및 락 경합 최소화 전략

| 컴포넌트 | 동기화 메커니즘 | 락 획득 범위 및 경합 최소화 전략 |
| :--- | :--- | :--- |
| **`RateLimiter`** | `threading.Lock` | • 토큰 보충 계산 및 잔여량 차감 구간만 최소 단위로 보호.<br/>• `blocking=True` 대기(`time.sleep`) 구간은 **락을 해제한 상태**에서 수행하여 타 스레드의 요청 진입을 블로킹하지 않음. |
| **`Stopwatch`** | `threading.Lock` | • `start()`, `stop()`, `lap()`, `reset()` 호출 시 내부 상태 변수 갱신 구간을 보호하여 다중 스레드 계측 환경에서 랩 기록 무결성 유지. |
| **`once`** | `threading.Lock` + Double-Checked Locking | • `has_run` 플래그를 락 없이 먼저 확인 후, 미실행 시에만 락 내부에서 2차 확인.<br/>• 실행 완료 후에는 락 없이 결과를 즉시 반환. |
| **`memoize`** | `threading.RLock` | • 재귀 함수 메모이제이션 시 동일 스레드 내 데드락을 방지하기 위해 `RLock` 채택.<br/>• 캐시 조회 및 갱신 시 보호. |
| **`debounce`** | `threading.Lock` | • 이전 예약된 `threading.Timer`의 취소(`timer.cancel()`) 및 신규 타이머 시작 구간을 원자적으로 동기화. |
| **`throttle`** | `threading.Lock` | • 마지막 실행 시각(`_last_called_time`) 비교 및 갱신을 원자적으로 처리하여 주기당 1회 실행 보장. |

---

### 4.2 핵심 시퀀스 다이어그램 (Mermaid Sequence Diagrams)

#### 1) `memoize` TTL 캐시 만료 및 재계산 흐름

동일한 키에 대해 복수의 스레드가 진입할 때, 캐시 히트, 만료 감지, `RLock` 하에서의 안전한 재계산 및 대기 스레드의 중복 연산 방지(Second Check Hit) 흐름을 나타냅니다.

```mermaid
sequenceDiagram
    autonumber
    actor ThreadA as 스레드 A
    actor ThreadB as 스레드 B
    participant Wrapper as MemoizeWrapper
    participant Lock as threading.RLock
    participant Cache as _cache (dict)
    participant Func as 대상 함수 (Target Function)

    Note over ThreadA, Cache: [1. 정상 캐시 히트 구간]
    ThreadA->>Wrapper: func("key-1") 호출
    Wrapper->>Wrapper: 인자 해시 키 생성 ("key-1")
    Wrapper->>Lock: acquire()
    Wrapper->>Cache: get("key-1")
    Cache-->>Wrapper: CacheEntry(val=100, expire_at=t0 + 60s)
    Wrapper->>Wrapper: now < expire_at 검증 (유효)
    Wrapper->>Lock: release()
    Wrapper-->>ThreadA: 100 반환 (함수 미실행)

    Note over ThreadA, Cache: [2. TTL 경과 후 만료 및 락 획득 재계산]
    Note over Wrapper: 시간 경과: now > expire_at
    ThreadA->>Wrapper: func("key-1") 호출
    Wrapper->>Lock: acquire()
    Wrapper->>Cache: get("key-1")
    Cache-->>Wrapper: CacheEntry(val=100, 만료됨)

    par 스레드 B 동시 진입 시도
        ThreadB->>Wrapper: func("key-1") 호출
        Wrapper->>Lock: acquire() 시도 (스레드 A가 락 보유 중이므로 대기)
    end

    Wrapper->>Func: 원본 함수 실행 ("key-1")
    Func-->>Wrapper: 105 (신규 계산 결과)
    Wrapper->>Cache: set("key-1", CacheEntry(val=105, expire_at=now + 60s))
    Wrapper->>Lock: release()
    Wrapper-->>ThreadA: 105 반환

    Note over ThreadB, Lock: [3. 대기하던 스레드 B의 2차 검증(Second Check) 캐시 히트]
    Lock-->>Wrapper: acquire() 성공 (ThreadB)
    Wrapper->>Cache: get("key-1")
    Cache-->>Wrapper: CacheEntry(val=105, expire_at=now + 60s)
    Wrapper->>Wrapper: now < expire_at 검증 통과 (Second Check Hit)
    Wrapper->>Lock: release()
    Wrapper-->>ThreadB: 105 반환 (함수 재실행 없이 신규 캐시값 즉시 반환)
```

---

#### 2) `RateLimiter` 토큰 버킷 획득 흐름

토큰 버킷 알고리즘에 기반하여, 가용 토큰 즉시 소비, 토큰 부족 시 락 해제 후 슬립 대기, 타임아웃 초과 시 거절 처리 흐름을 나타냅니다.

```mermaid
sequenceDiagram
    autonumber
    actor Caller as 호출자 (Worker Thread)
    participant Limiter as RateLimiter
    participant Lock as threading.Lock
    participant Clock as time.perf_counter_ns()
    participant Sleeper as time.sleep()

    Caller->>Limiter: acquire(tokens=1.0, blocking=True, timeout=5.0)
    Limiter->>Lock: acquire()
    Limiter->>Clock: 현재 시각 확인 (now)
    Limiter->>Limiter: 경과 시간 계산: Δt = now - last_refill
    Limiter->>Limiter: 토큰 보충: tokens = min(burst, tokens + Δt * rate)
    Limiter->>Limiter: last_refill = now

    alt 가용 토큰 충분 (tokens >= 1.0)
        Limiter->>Limiter: tokens -= 1.0 (토큰 차감)
        Limiter->>Lock: release()
        Limiter-->>Caller: True 반환 (작업 즉시 진행)
    else 가용 토큰 부족 및 blocking=True 대기 허용
        Limiter->>Limiter: 필요 토큰량 계산: needed = 1.0 - tokens
        Limiter->>Limiter: 대기 시간 계산: wait_seconds = needed / rate
        
        alt wait_seconds <= timeout
            Limiter->>Lock: release() (중요: 다른 스레드를 위해 락 해제 후 대기)
            Limiter->>Sleeper: sleep(wait_seconds)
            Sleeper-->>Limiter: 대기 완료
            
            Limiter->>Lock: acquire()
            Limiter->>Clock: 현재 시각 재확인
            Limiter->>Limiter: 잔여 토큰 재계산 및 1.0 차감
            Limiter->>Lock: release()
            Limiter-->>Caller: True 반환 (대기 후 작업 진행)
        else wait_seconds > timeout (타임아웃 한도 초과)
            Limiter->>Lock: release()
            Limiter-->>Caller: False 반환 (요청 거절)
        end
    else non-blocking (blocking=False)
        Limiter->>Lock: release()
        Limiter-->>Caller: False 반환 (즉시 거절)
    end
```

---

#### 3) `retry` 지수 백오프 및 Full Jitter 흐름

네트워크 또는 일시적 I/O 장애 발생 시 지수 백오프($T_{\text{temp}} = \min(M, B \times 2^{k-1})$)와 Full Jitter($T_{\text{wait}} \sim U(0, T_{\text{temp}})$)를 통해 재시도 후 복구되는 흐름입니다.

```mermaid
sequenceDiagram
    autonumber
    actor Client as 비즈니스 서비스
    participant Decorator as @retry 래퍼
    participant Target as 대상 함수 (I/O 작업)
    participant JitterEngine as 지수 백오프 & Full Jitter 계산기
    participant Sleeper as time.sleep / asyncio.sleep

    Client->>Decorator: execute_action(*args, **kwargs)
    
    rect rgb(255, 240, 240)
        note right of Decorator: [1차 시도 (k=1)]
        Decorator->>Target: 함수 실행
        Target-->>Decorator: ConnectionResetError 발생 (대상 예외 포착)
        Decorator->>Decorator: k < max_attempts (1 < 3) 확인
        Decorator->>JitterEngine: calculate_backoff(k=1, base=0.5, max=60.0, jitter=True)
        JitterEngine->>JitterEngine: T_temp = min(60.0, 0.5 * 2^0) = 0.5s
        JitterEngine->>JitterEngine: T_wait = Uniform(0, 0.5s) -> 0.31s
        JitterEngine-->>Decorator: 0.31s
        opt on_retry 콜백 등록 시
            Decorator->>Decorator: on_retry(exc, attempt=1, wait_time=0.31)
        end
        Decorator->>Sleeper: sleep(0.31s)
        Sleeper-->>Decorator: 대기 완료
    end

    rect rgb(255, 248, 240)
        note right of Decorator: [2차 재시도 (k=2)]
        Decorator->>Target: 함수 재실행
        Target-->>Decorator: TimeoutError 발생 (대상 예외 포착)
        Decorator->>Decorator: k < max_attempts (2 < 3) 확인
        Decorator->>JitterEngine: calculate_backoff(k=2, base=0.5, max=60.0, jitter=True)
        JitterEngine->>JitterEngine: T_temp = min(60.0, 0.5 * 2^1) = 1.0s
        JitterEngine->>JitterEngine: T_wait = Uniform(0, 1.0s) -> 0.82s
        JitterEngine-->>Decorator: 0.82s
        opt on_retry 콜백 등록 시
            Decorator->>Decorator: on_retry(exc, attempt=2, wait_time=0.82)
        end
        Decorator->>Sleeper: sleep(0.82s)
        Sleeper-->>Decorator: 대기 완료
    end

    rect rgb(240, 255, 240)
        note right of Decorator: [3차 재시도 (k=3)]
        Decorator->>Target: 함수 재실행
        Target-->>Decorator: 결과값 반환 (성공)
        Decorator->>Decorator: 성공 감지 -> 재시도 루프 종료
    end

    Decorator-->>Client: 결과값 반환
```

---

## 5. 공개 SDK 인터페이스 상세 명세 (Public SDK Interface Specification)

> [!IMPORTANT]
> **OpenAPI 규격 대체 근거**:
> 본 프로젝트는 원격 HTTP 웹 서비스를 제공하는 API 서버가 아니라, 개발자가 애플리케이션 내부에서 직접 임포트하여 사용하는 **Python 유틸리티 라이브러리 및 SDK**입니다. 따라서 원격 네트워크 엔드포인트를 명세하는 OpenAPI YAML 규격 대신, PEP 484/585/612 표준을 따르는 **Python SDK 공개 함수/클래스 상세 타입 시그니처(인자, 제네릭 매개변수, 반환값, 발생 예외, 코드 예제)**로 갈음하여 명시합니다.

---

### 5.1 최상위 공개 진입점 (`quiver/__init__.py`)

35종의 공개 심볼은 최상위 네임스페이스에서 즉시 임포트할 수 있습니다.

```python
"""quiver: Modern, zero-dependency, fully type-safe utility quiver for Python engineers."""

from quiver.collections import (
    chunk,
    flatten,
    group_by,
    key_by,
    partition,
    uniq_by,
    windowed,
    deep_get,
    deep_set,
    deep_merge,
    pick,
    omit,
    invert,
)
from quiver.behavior import (
    pipe,
    compose,
    curry,
    once,
    debounce,
    throttle,
    memoize,
    retry,
)
from quiver.strings import (
    to_camel_case,
    to_snake_case,
    to_kebab_case,
    to_pascal_case,
    slugify,
    truncate,
    mask_sensitive,
)
from quiver.scope import (
    let,
    also,
    tap,
    take_if,
    take_unless,
    coalesce,
)
from quiver.timing import (
    Stopwatch,
    measure_time,
    RateLimiter,
)

__all__ = [
    # Collections (13)
    "chunk",
    "flatten",
    "group_by",
    "key_by",
    "partition",
    "uniq_by",
    "windowed",
    "deep_get",
    "deep_set",
    "deep_merge",
    "pick",
    "omit",
    "invert",
    # Behavior (8)
    "pipe",
    "compose",
    "curry",
    "once",
    "debounce",
    "throttle",
    "memoize",
    "retry",
    # Strings (7)
    "to_camel_case",
    "to_snake_case",
    "to_kebab_case",
    "to_pascal_case",
    "slugify",
    "truncate",
    "mask_sensitive",
    # Scope (6)
    "let",
    "also",
    "tap",
    "take_if",
    "take_unless",
    "coalesce",
    # Timing (3)
    "Stopwatch",
    "measure_time",
    "RateLimiter",
]
```

---

### 5.2 컬렉션 모듈 (`quiver/collections.py`)

#### 1) `chunk`
- **설명**: 입력 이터러블을 크기 `size`의 리스트를 산출하는 지연 제너레이터로 분할합니다. 잔여 원소는 마지막 청크에 포함됩니다.
- **시그니처**:
  ```python
  def chunk(
      iterable: Iterable[T],
      size: int,
      step: Optional[int] = None,
  ) -> Iterator[list[T]]: ...
  ```
- **매개변수**:
  - `iterable` (`Iterable[T]`): 분할할 시퀀스 또는 제너레이터.
  - `size` (`int`): 청크당 원소 수 ($\ge 1$).
  - `step` (`Optional[int]`): 다음 청크 시작 간격 ($\ge 1$). 기본값 `None` 시 `size`와 동일하게 동작.
- **반환값**: `Iterator[list[T]]` - 분할된 리스트 제너레이터.
- **발생 예외**:
  - `ValueError`: `size < 1` 또는 `step < 1`인 경우.
  - `TypeError`: `iterable`이 순회 불가능한 객체인 경우.

#### 2) `flatten`
- **설명**: 중첩된 이터러블을 `depth` 깊이까지 평탄화합니다. `str`, `bytes`, `bytearray`, `Mapping`은 원자 객체로 취급되어 분해되지 않습니다.
- **시그니처**:
  ```python
  def flatten(
      iterable: Iterable[Any],
      depth: Optional[int] = None,
  ) -> Iterator[Any]: ...
  ```
- **매개변수**:
  - `iterable` (`Iterable[Any]`): 중첩 이터러블.
  - `depth` (`Optional[int]`): 최대 평탄화 깊이 ($\ge 0$). 기본값 `None`은 무한 깊이 재귀.
- **반환값**: `Iterator[Any]` - 평탄화된 단일 원소 제너레이터.
- **발생 예외**:
  - `ValueError`: `depth < 0`이거나 순환 참조(Cyclic Reference) 감지 시.
  - `TypeError`: `iterable`이 순회 불가능한 객체인 경우.

#### 3) `group_by`
- **설명**: 컬렉션의 원소들을 `key_fn(item)` 기준 딕셔너리로 분류합니다. 각 키 내부 리스트는 원래 원소의 등장 순서를 보존합니다.
- **시그니처**:
  ```python
  def group_by(
      iterable: Iterable[T],
      key_fn: Callable[[T], K],
  ) -> dict[K, list[T]]: ...
  ```
- **매개변수**:
  - `iterable` (`Iterable[T]`): 대상 컬렉션.
  - `key_fn` (`Callable[[T], K]`): 키 추출 함수 ($K$는 `Hashable`).
- **반환값**: `dict[K, list[T]]` - 키별 원소 리스트 매핑.
- **발생 예외**:
  - `TypeError`: `key_fn`이 호출 불가능하거나 추출된 키가 해시 불가한 경우.

#### 4) `key_by`
- **설명**: 컬렉션의 각 원소로부터 키를 추출하여 단일 원소 딕셔너리를 생성합니다. 키 중복 시 마지막 원소가 이전 원소를 덮어씁니다.
- **시그니처**:
  ```python
  def key_by(
      iterable: Iterable[T],
      key_fn: Callable[[T], K],
  ) -> dict[K, T]: ...
  ```
- **매개변수**:
  - `iterable` (`Iterable[T]`): 대상 컬렉션.
  - `key_fn` (`Callable[[T], K]`): 고유 키 추출 함수.
- **반환값**: `dict[K, T]` - 키-원소 딕셔너리.
- **발생 예외**:
  - `TypeError`: `key_fn`이 호출 불가능한 경우.

#### 5) `partition`
- **설명**: 술어 함수 `predicate(item)`의 평가 결과에 따라 `(참_리스트, 거짓_리스트)`의 불변 튜플로 양분합니다.
- **시그니처**:
  ```python
  def partition(
      predicate: Callable[[T], bool],
      iterable: Iterable[T],
  ) -> tuple[list[T], list[T]]: ...
  ```
- **매개변수**:
  - `predicate` (`Callable[[T], bool]`): 진위 판별 함수.
  - `iterable` (`Iterable[T]`): 대상 컬렉션.
- **반환값**: `tuple[list[T], list[T]]` - `([참 원소들], [거짓 원소들])` 튜플.
- **발생 예외**:
  - `TypeError`: `predicate`가 호출 불가능한 경우.

#### 6) `uniq_by`
- **설명**: 원래 등장 순서를 유지하며 고유 원소만을 추출합니다. 해시 불가한 가변 객체는 안전 문자열 폴백으로 고유성을 판별합니다.
- **시그니처**:
  ```python
  def uniq_by(
      iterable: Iterable[T],
      key_fn: Optional[Callable[[T], Any]] = None,
  ) -> list[T]: ...
  ```
- **매개변수**:
  - `iterable` (`Iterable[T]`): 대상 컬렉션.
  - `key_fn` (`Optional[Callable[[T], Any]]`): 고유성 판별 키 함수 (생략 시 원소 자체).
- **반환값**: `list[T]` - 중복이 제거된 순서 보존 리스트.

#### 7) `windowed`
- **설명**: 크기 `size`, 보폭 `step`의 슬라이딩 윈도우 튜플 제너레이터를 산출합니다.
- **시그니처**:
  ```python
  def windowed(
      iterable: Iterable[T],
      size: int,
      step: int = 1,
      fill_value: Any = _MISSING,
  ) -> Iterator[tuple[Any, ...]]: ...
  ```
- **매개변수**:
  - `size` (`int`): 윈도우 크기 ($\ge 1$).
  - `step` (`int`): 이동 간격 ($\ge 1$).
  - `fill_value` (`Any`): 마지막 불완전 윈도우 패딩 값 (생략 시 불완전 윈도우는 산출하지 않고 종료).
- **반환값**: `Iterator[tuple[Any, ...]]` - 슬라이딩 윈도우 튜플 제너레이터.
- **발생 예외**:
  - `ValueError`: `size < 1` 또는 `step < 1`인 경우.

#### 8) `deep_get`
- **설명**: 점(`.`) 구분 경로 문자열 또는 키/인덱스 시퀀스로 중첩 매핑을 탐색합니다. 경로 미존재 시 `default`를 안전 반환합니다.
- **시그니처**:
  ```python
  def deep_get(
      mapping: Mapping[str, Any],
      path: Union[str, Sequence[Union[str, int]]],
      default: Optional[D] = None,
      *,
      separator: str = ".",
  ) -> Union[Any, D]: ...
  ```
- **매개변수**:
  - `mapping` (`Mapping[str, Any]`): 중첩 딕셔너리.
  - `path`: 경로 문자열 (예: `"user.profile.age"`) 또는 시퀀스 (`["user", "profile", "age"]`).
  - `default` (`Optional[D]`): 키 부재 시 반환값.
  - `separator` (`str`): 경로 구분자 (기본 `"."`).
- **반환값**: 찾은 값 또는 `default`.

#### 9) `deep_set`
- **설명**: 중첩 딕셔너리의 지정 경로에 값을 설정한 신규 딕셔너리를 반환합니다(Copy-on-Write). 원본은 변이되지 않습니다.
- **시그니처**:
  ```python
  def deep_set(
      mapping: Mapping[str, Any],
      path: Union[str, Sequence[Union[str, int]]],
      value: Any,
      *,
      separator: str = ".",
  ) -> dict[str, Any]: ...
  ```
- **발생 예외**:
  - `ValueError`: `path`가 비어있는 경우.

#### 10) `deep_merge`
- **설명**: 복수의 딕셔너리를 좌에서 우로 심층 병합한 신규 딕셔너리를 반환합니다.
- **시그니처**:
  ```python
  def deep_merge(
      *mappings: Mapping[K, V],
      deep: bool = True,
  ) -> dict[K, V]: ...
  ```
- **발생 예외**:
  - `TypeError`: 전달된 인자가 `Mapping` 인터페이스를 구현하지 않은 경우.

#### 11) `pick` 및 `omit`
- **설명**: 지정된 키 화이트리스트(`pick`) 또는 블랙리스트(`omit`) 기준으로 새 딕셔너리를 필터링합니다.
- **시그니처**:
  ```python
  def pick(mapping: Mapping[K, V], *keys: K) -> dict[K, V]: ...
  def omit(mapping: Mapping[K, V], *keys: K) -> dict[K, V]: ...
  ```

#### 12) `invert`
- **설명**: 딕셔너리의 키와 값을 반전합니다. `multi=True` 시 중복 값에 대해 키 리스트(`dict[V, list[K]]`)를 생성합니다.
- **시그니처**:
  ```python
  @overload
  def invert(mapping: Mapping[K, V], *, multi: Literal[False] = False) -> dict[V, K]: ...
  @overload
  def invert(mapping: Mapping[K, V], *, multi: Literal[True]) -> dict[V, list[K]]: ...
  def invert(
      mapping: Mapping[K, V],
      *,
      multi: bool = False,
  ) -> Union[dict[V, K], dict[V, list[K]]]: ...
  ```

---

### 5.3 함수 동작 및 실행 제어 모듈 (`quiver/behavior.py`)

#### 1) `pipe` 및 `compose`
- **설명**:
  - `pipe(val, f, g)`: $val \rightarrow f(val) \rightarrow g(f(val))$ 좌에서 우로 단방향 파이프라인 변환.
  - `compose(g, f)`: $(g \circ f)(x) = g(f(x))$ 우에서 좌로 실행되는 신규 합성 함수 생성.
- **시그니처**:
  ```python
  def pipe(value: Any, *fns: Callable[[Any], Any]) -> Any: ...
  def compose(*fns: Callable[[Any], Any]) -> Callable[..., Any]: ...
  ```
- **발생 예외**:
  - `TypeError`: 인자로 호출 불가능한 객체가 전달된 경우.

#### 2) `curry`
- **설명**: 다인자 함수를 단일/부분 인자를 받는 체이닝 함수로 변환합니다. 인자가 모두 충족되면 원본 함수를 실행합니다.
- **시그니처**:
  ```python
  def curry(
      fn: Callable[..., R],
      arity: Optional[int] = None,
  ) -> Callable[..., Any]: ...
  ```
- **발생 예외**:
  - `ValueError`: 가변 인자(`*args`, `**kwargs`) 함수에 대해 `arity`가 지정되지 않은 경우.

#### 3) `once`
- **설명**: 멀티스레드 환경에서 정확히 1회 실행을 보장(Double-Checked Locking)하는 데코레이터입니다. 원본 함수 실행 중 예외 발생 시 실패 상태를 캐싱하지 않아 다음 호출자에게 재실행 기회를 부여합니다.
- **시그니처**:
  ```python
  def once(fn: Callable[P, R]) -> Callable[P, R]: ...
  ```
- **제공 속성**:
  - `wrapper.reset()`: 실행 플래그 및 캐시를 초기화하여 재실행을 허용.

#### 4) `debounce`
- **설명**: 마지막 호출 후 `wait_seconds` 동안 추가 호출이 없을 때까지 실행을 지연하는 데코레이터입니다.
- **시그니처**:
  ```python
  def debounce(
      wait_seconds: float,
  ) -> Callable[[Callable[P, R]], Callable[P, Optional[R]]]: ...
  ```
- **제공 속성**:
  - `wrapper.cancel()`: 예약된 타이머를 취소.
  - `wrapper.flush()`: 대기 중인 작업을 즉시 실행.
- **발생 예외**:
  - `ValueError`: `wait_seconds <= 0`인 경우.

#### 5) `throttle`
- **설명**: 지정 주기(`interval_seconds`) 내 최대 1회만 실행되도록 호출 빈도를 제한하는 데코레이터입니다.
- **시그니처**:
  ```python
  def throttle(
      interval_seconds: float,
  ) -> Callable[[Callable[P, R]], Callable[P, Optional[R]]]: ...
  ```
- **발생 예외**:
  - `ValueError`: `interval_seconds <= 0`인 경우.

#### 6) `memoize`
- **설명**: 초 단위 유효시간(TTL) 및 최대 용량(`maxsize`)을 지원하는 멀티스레드 안전(`threading.RLock`) 메모이제이션 데코레이터입니다.
- **시그니처**:
  ```python
  def memoize(
      ttl_seconds: Optional[float] = None,
      maxsize: Optional[int] = 128,
      key_fn: Optional[Callable[..., Hashable]] = None,
  ) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
  ```
- **제공 속성**:
  - `wrapper.cache_clear()`: 모든 캐시 삭제.
  - `wrapper.cache_info()`: 히트 수, 미스 수, 현재 캐시 크기 딕셔너리 반환.

#### 7) `retry`
- **설명**: 지수 백오프 및 Full Jitter 알고리즘을 적용한 재시도 데코레이터입니다. 동기 함수 및 비동기 코루틴(`async def`)을 자동 감지하여 지원합니다. 치명적 시스템 예외(`KeyboardInterrupt`, `SystemExit`)는 포착하지 않고 즉시 전파합니다.
- **시그니처**:
  ```python
  def retry(
      max_attempts: int = 3,
      backoff_base: float = 0.5,
      backoff_max: float = 60.0,
      jitter: bool = True,
      exceptions: tuple[type[Exception], ...] = (Exception,),
      on_retry: Optional[Callable[[Exception, int, float], None]] = None,
  ) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
  ```
- **매개변수**:
  - `max_attempts` (`int`): 최대 시도 횟수 ($\ge 1$).
  - `backoff_base` (`float`): 기본 지연 시간(초) ($> 0.0$).
  - `backoff_max` (`float`): 최대 대기 상한(초) ($\ge \text{backoff\_base}$).
  - `jitter` (`bool`): Full Jitter($\text{Uniform}(0, T_{\text{backoff}})$) 적용 여부.
  - `exceptions` (`tuple[type[Exception], ...]`): 재시도 대상 예외 튜플.
  - `on_retry` (`Optional[Callable[[Exception, int, float], None]]`): 재시도 대기 전 실행되는 콜백.

---

### 5.4 문자열 변환 및 보안 모듈 (`quiver/strings.py`)

#### 1) 케이스 변환군 (`to_camel_case`, `to_snake_case`, `to_kebab_case`, `to_pascal_case`)
- **설명**: 문자열 표기법을 상호 변환합니다. `None` 전달 시 빈 문자열(`""`)을 반환합니다.
- **시그니처**:
  ```python
  def to_camel_case(text: Optional[str]) -> str: ...
  def to_snake_case(text: Optional[str]) -> str: ...
  def to_kebab_case(text: Optional[str]) -> str: ...
  def to_pascal_case(text: Optional[str]) -> str: ...
  ```

#### 2) `slugify`
- **설명**: 유니코드 정규화(NFKD) 및 특수문자 하이픈 치환을 거쳐 URL 친화적 정규 슬러그를 생성합니다.
- **시그니처**:
  ```python
  def slugify(
      text: Optional[str],
      separator: str = "-",
      allow_unicode: bool = False,
  ) -> str: ...
  ```

#### 3) `truncate`
- **설명**: 문자열을 `length` 길이로 자르고 `suffix`를 부착합니다. `preserve_words=True` 시 단어 중간 절단을 방지합니다. 결과 길이는 항상 $\le \text{length}$입니다.
- **시그니처**:
  ```python
  def truncate(
      text: Optional[str],
      length: int,
      suffix: str = "...",
      preserve_words: bool = True,
  ) -> str: ...
  ```
- **발생 예외**:
  - `ValueError`: `length < len(suffix)`인 경우.

#### 4) `mask_sensitive`
- **설명**: 개인정보 및 금융 식별자를 표준 패턴에 따라 마스킹 문자(`mask_char`)로 대체합니다.
  - `email`: `local-part` 중간 마스킹, 도메인 보존 (`u***r@example.com`).
  - `phone`: 국번/가운데 자리 마스킹 (`010-****-1234`).
  - `rrn`: 주민등록번호 뒤 6자리 마스킹 (`900101-1******`).
  - `card`: 신용카드 중간 6자리 마스킹 (`1234-56**-****-3456`).
- **시그니처**:
  ```python
  def mask_sensitive(
      text: Optional[str],
      pattern_type: Optional[Literal["email", "phone", "rrn", "card"]] = None,
      mask_char: str = "*",
      keep_prefix: int = 0,
      keep_suffix: int = 0,
  ) -> str: ...
  ```
- **발생 예외**:
  - `ValueError`: `len(mask_char) != 1`이거나 미지원 `pattern_type`인 경우.

---

### 5.5 스코프 확장 및 널 안전 모듈 (`quiver/scope.py`)

#### 1) `let`
- **설명**: 객체를 변환 함수 `block`에 전달하고 그 결과를 반환합니다.
- **시그니처**:
  ```python
  def let(target: T, block: Callable[[T], R]) -> R: ...
  ```

#### 2) `also` 및 `tap`
- **설명**: 객체를 부수 효과 함수 `block`에 전달하여 실행한 뒤, 반환값과 무관하게 원본 `target` 참조를 그대로 반환합니다 ($\text{result} \equiv \text{target}$).
- **시그니처**:
  ```python
  def also(target: T, block: Callable[[T], Any]) -> T: ...
  def tap(target: T, block: Callable[[T], Any]) -> T: ...
  ```

#### 3) `take_if` 및 `take_unless`
- **설명**:
  - `take_if`: `predicate(target)`이 `True`이면 `target`, `False`이면 `None` 반환.
  - `take_unless`: `predicate(target)`이 `True`이면 `None`, `False`이면 `target` 반환.
- **시그니처**:
  ```python
  def take_if(target: T, predicate: Callable[[T], bool]) -> Optional[T]: ...
  def take_unless(target: T, predicate: Callable[[T], bool]) -> Optional[T]: ...
  ```

#### 4) `coalesce`
- **설명**: 가변 인자 중 최초로 발견되는 `is not None` 값을 반환하며, 모두 `None`인 경우 `default`를 반환합니다.
- **시그니처**:
  ```python
  def coalesce(
      *values: Optional[T],
      default: Optional[T] = None,
  ) -> Optional[T]: ...
  ```

---

### 5.6 고정밀 시간 측정 및 호출율 제어 모듈 (`quiver/timing.py`)

#### 1) `Stopwatch`
- **설명**: `time.perf_counter_ns()` 단조 시계를 사용하는 고정밀 스톱워치입니다. 구간 기록(Lap time) 및 `with` 컨텍스트 매니저를 지원합니다.
- **시그니처**:
  ```python
  @dataclass(frozen=True)
  class LapRecord:
      index: int
      name: Optional[str]
      lap_time_ns: int
      total_time_ns: int
      lap_seconds: float
      total_seconds: float

  class Stopwatch:
      def __init__(self) -> None: ...
      @property
      def is_running(self) -> bool: ...
      @property
      def elapsed_ns(self) -> int: ...
      @property
      def elapsed_seconds(self) -> float: ...
      @property
      def laps(self) -> list[LapRecord]: ...
      def start(self) -> "Stopwatch": ...
      def stop(self) -> float: ...
      def reset(self) -> "Stopwatch": ...
      def lap(self, name: Optional[str] = None) -> LapRecord: ...
      def __enter__(self) -> "Stopwatch": ...
      def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
  ```

#### 2) `measure_time`
- **설명**: 코드 블록 또는 함수의 소요 시간을 지정 단위(`s`, `ms`, `us`, `ns`)로 측정하는 컨텍스트 매니저 겸 데코레이터입니다.
- **시그니처**:
  ```python
  def measure_time(
      callback: Optional[Callable[[float], None]] = None,
      unit: Literal["s", "ms", "us", "ns"] = "ms",
  ) -> MeasureTimeContext: ...
  ```

#### 3) `RateLimiter`
- **설명**: 토큰 버킷 알고리즘 기반 멀티스레드 안전 호출율 제한기입니다. 데코레이터, 컨텍스트 매니저, 메서드 직접 호출(`acquire`)을 지원합니다.
- **시그니처**:
  ```python
  class RateLimiter:
      def __init__(
          self,
          rate: float,
          per_seconds: float = 1.0,
          burst: Optional[float] = None,
      ) -> None: ...
      @property
      def available_tokens(self) -> float: ...
      def acquire(
          self,
          tokens: float = 1.0,
          blocking: bool = True,
          timeout: Optional[float] = None,
      ) -> bool: ...
      def __enter__(self) -> bool: ...
      def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
      def __call__(self, fn: Callable[P, R]) -> Callable[P, R]: ...
  ```
- **발생 예외**:
  - `ValueError`: `rate <= 0`이거나 `per_seconds <= 0`, 또는 요청 토큰 수가 `burst` 용량을 초과하는 경우.

---

## 6. 실무 적용 예제 (Engineering Use Cases)

```python
import quiver

# 1. Collections: 데이터 파이프라인 청킹 및 중첩 딕셔너리 안전 조작
raw_events = [
    {"event_id": 1, "payload": {"user": {"tier": "vip"}}},
    {"event_id": 2, "payload": {"user": {"tier": "free"}}},
    {"event_id": 3, "payload": {"user": {"tier": "vip"}}},
]

# 2건 단위 청킹 스트리밍
for batch in quiver.chunk(raw_events, size=2):
    print(f"Processing batch of size {len(batch)}")

# 중첩 경로 안전 탐색 및 불변 업데이트
first_tier = quiver.deep_get(raw_events[0], "payload.user.tier", default="unknown")
updated_event = quiver.deep_set(raw_events[0], "payload.processed", True)

# 2. Behavior: 지수 백오프 재시도 및 스레드 세이프 캐싱
@quiver.retry(max_attempts=3, backoff_base=0.2, jitter=True)
@quiver.memoize(ttl_seconds=30.0, maxsize=256)
def query_payment_gateway(order_id: str) -> dict:
    # 일시적 네트워크 예외 발생 시 Full Jitter 지수 백오프로 자동 재시도
    return {"order_id": order_id, "status": "CONFIRMED"}

# 3. Strings: 개인정보 마스킹 및 케이스 변환
masked_user_email = quiver.mask_sensitive("backend_dev@company.io", pattern_type="email")
# -> "b*********v@company.io"
db_column_name = quiver.to_snake_case("totalPaymentAmount")
# -> "total_payment_amount"

# 4. Scope: Kotlin 스타일 선언적 스코프 체이닝
def process_user_input(raw_name: str | None) -> str:
    return quiver.let(
        quiver.coalesce(raw_name, default="guest"),
        lambda name: name.strip().lower(),
    )

# 5. Timing: 외부 API 호출율 제한 및 소요 시간 프로파일링
api_limiter = quiver.RateLimiter(rate=50, per_seconds=1.0)  # 초당 50회 제한

@api_limiter
def sync_external_inventory():
    with quiver.measure_time(unit="ms") as timer:
        # 고정밀 계측 대상 I/O 로직 수행
        pass
    if timer.elapsed > 100.0:
        print(f"Warning: Latency spike detected ({timer.elapsed:.2f} {timer.unit})")
```
