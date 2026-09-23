# [quiver] 5-Pillar 코드 품질 감사 및 리뷰 보고서 (Code Review Report)

- **검토일자**: 2026-09-23
- **검토자**: 시니어 백엔드 테크리드 / 코드 리뷰어 (`backend-code-reviewer`)
- **검토 대상 모듈**: `quiver` 코어 유틸리티 패키지 및 전체 테스트 스위트 ([`quiver/`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver), [`tests/`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests))
- **최종 판정**: **APPROVED (승인)**

---

## 1. 5-Pillar 코드 품질 감사 매트릭스 (5-Pillar Audit)

| 감사 필라 (Pillar) | 세부 검토 기준 | 평가 점수 (1~5) | 검토 소견 및 실무 감사 의견 |
| :--- | :--- | :---: | :--- |
| **Pillar 1: 아키텍처 정합성** | Zero-Dependency 런타임 의존성 0개 검증, 5대 도메인 모듈 경계([`01_SYSTEM_DESIGN.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/system-designer/01_SYSTEM_DESIGN.md)), ADR-001([`01_ARCHITECTURE_ADR.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/fullstack-architect/01_ARCHITECTURE_ADR.md)) 설계 일치도 | 5 / 5 | `pyproject.toml` 상 `dependencies = []`로 외부 런타임 의존성이 전혀 없습니다. 5대 도메인 모듈 간 수평 임포트가 없으며, 최상위 `__init__.py`에서 선별된 35개 심볼을 `__all__`로 격리하여 네임스페이스 오염을 방지했습니다. |
| **Pillar 2: 클린코드 & 타입 안정성** | PEP 561 [`py.typed`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/py.typed) 배포, PEP 612 `ParamSpec`/`TypeVar` 시그니처 보존, Copy-on-Write 불변성 | 4.5 / 5 | 데코레이터 적용 시 원본 함수의 매개변수와 반환 타입을 보존하며, 컬렉션 조작 함수가 원본을 변형하지 않는 Copy-on-Write를 지킵니다. 다만 래퍼 클래스의 `Generic[P, R]` 상속 누락 건은 개선이 필요합니다. |
| **Pillar 3: 보안 & 방어 프로그래밍**| 사전 컴파일 정규식 기반 ReDoS 방어, 재귀 DFS 방문 추적을 통한 순환 참조 방어, 개인정보/금융 데이터 마스킹, 시스템 시그널 전파 | 5 / 5 | 정규식 패턴 전수 `re.compile` 처리로 런타임 지연과 Catastrophic Backtracking을 배제했습니다. `visited_ids` 기반 순환 참조 차단과 시스템 종료 시그널 즉시 전파가 견고하게 구현되었습니다. |
| **Pillar 4: 성능 & 동시성**| OS 단조 시계 [`Stopwatch`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L37-L122), [`memoize`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L313-L324)의 `threading.RLock`, 원자적 [`RateLimiter`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L210-L321) 토큰 버킷, 제너레이터 스트리밍 | 4.5 / 5 | 나노초 단조 시계 기반 왜곡 방지 및 토큰 버킷 락 해제 후 슬립 패턴이 우수합니다. `memoize`의 락 내부 함수 실행 구조와 제너레이터 1회성 소진 특성은 호출부 유의사항으로 안내가 필요합니다. |
| **Pillar 5: 테스트 품질 & 커버리지**| Red-Green TDD 실행 여부, 194개 단위/통합 테스트 통과, 99% 라인 커버리지, 100 멀티스레드 동시성 스트레스 검증 | 5 / 5 | 총 194개 테스트가 0.98초 만에 통과했으며, 전체 788문장 중 6문장을 제외한 99% 라인 커버리지를 확인했습니다. `threading.Barrier(100)` 기반 100개 스레드 경합 테스트를 모두 통과했습니다. |

---

### 1.1 Pillar 1: 아키텍처 정합성 상세 검토

1. **Zero-Dependency 런타임 의존성 검증**:
   - [`pyproject.toml:L26`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/pyproject.toml#L26)의 `dependencies = []` 설정을 확인했습니다.
   - 소스 코드([`quiver/`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver)) 전반에서 `toolz`, `pydash`, `tenacity`, `more-itertools` 같은 외부 서드파티 패키지 임포트가 전혀 없습니다. 오직 Python 3.10+ 내장 모듈(`collections`, `itertools`, `functools`, `threading`, `time`, `re`, `unicodedata`, `inspect`, `random`, `dataclasses`)만으로 전체 기능을 구현했습니다.
   - 외부 런타임 의존성이 없으므로 다운스트림 서비스에서 발생할 수 있는 패키지 버전 충돌(Dependency Hell)과 공급망 보안(CVE) 위험을 구조적으로 제거했습니다.
   - *트레이드오프*: 순수 표준 라이브러리만을 활용하므로 C-Extension이나 Rust FFI(PyO3) 가속 라이브러리에 비해 수천만 건 수준의 대용량 컬렉션 순회 시 순수 파이썬 루프 오버헤드가 발생할 수 있습니다. 이는 라이브러리 설계 의도(경량화 및 무의존성)에 부합하는 수용 가능한 트레이드오프입니다.

2. **5대 도메인 모듈 경계 및 관심사 분리**:
   - 모듈 구조가 설계서([`01_SYSTEM_DESIGN.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/system-designer/01_SYSTEM_DESIGN.md)) 1.2절의 정의와 정확히 일치합니다:
     - [`quiver.collections`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py): 컬렉션 청킹, 슬라이딩 윈도우, 평탄화, 불변 갱신 (13개 함수)
     - [`quiver.behavior`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py): 함수 파이프, 커링, 디바운스, 쓰로틀, 캐싱, 재시도 제어 (8개 함수/클래스)
     - [`quiver.strings`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py): 명명 규칙 케이스 변환, 슬러그화, 단어 보존 자르기, 데이터 마스킹 (7개 함수)
     - [`quiver.scope`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py): 표현식 체이닝, 부수효과 탭, 조건 필터링, 널 안전 단락 평가 (6개 함수)
     - [`quiver.timing`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py): 단조 스톱워치, 실행시간 계측 컨텍스트, 토큰 버킷 속도 제어 (3개 클래스/함수)
   - 모듈 간 교차 임포트(Cross-Module Import)가 존재하지 않아 순환 참조 위험이 없습니다.
   - 최상위 진입점 [`quiver/__init__.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/__init__.py#L51-L94)에서 `__all__`을 명시하여 내부 헬퍼 객체를 은닉하고 총 35개 공개 인터페이스만 노출하도록 통제했습니다.

3. **계약 통합(Contract Integrator) 생략의 기술적 타당성**:
   - 본 패키지는 HTTP 엔드포인트를 서빙하는 웹 애플리케이션이 아닌 순수 인메모리 유틸리티 라이브러리이므로, OpenAPI/MSW 기반의 계약 검증 계층을 생략한 결정([`01_ARCHITECTURE_ADR.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/fullstack-architect/01_ARCHITECTURE_ADR.md) 원칙 6)은 실무 관점에서 타당합니다. PEP 561 마커와 엄격한 단위 테스트 스위트가 인터페이스 계약을 안정적으로 담보하고 있습니다.

---

### 1.2 Pillar 2: 클린코드 & 타입 안정성 상세 검토

1. **PEP 561 마커 및 패키징 준수**:
   - 패키지 루트에 [`quiver/py.typed`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/py.typed) 마커 파일이 배치되어, 패키지를 설치한 외부 프로젝트의 `mypy --strict` 및 IDE 환경에서 타입 힌트가 누락 없이 인식됩니다.

2. **PEP 612 `ParamSpec`을 통한 함수 시그니처 보존**:
   - [`quiver.behavior.retry`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L326-L386):
     ```python
     P = ParamSpec("P")
     R = TypeVar("R")

     def retry(...) -> Callable[[Callable[P, R]], Callable[P, R]]:
     ```
     데코레이터 래핑 시 `Callable[..., Any]`로 인자 정보가 유실되지 않고, 원본 함수의 인자 시그니처와 반환 타입이 정적 분석기에 보존됩니다.
   - [`quiver.collections.invert`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L355-L372):
     `@overload` 데코레이터를 적용하여 `multi=False`일 때는 `dict[V, K]`, `multi=True`일 때는 `dict[V, list[K]]`로 반환 타입이 자동 분기되도록 설계했습니다.

3. **Copy-on-Write (CoW) 기반 불변성 검증**:
   - [`deep_set`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L267-L299):
     인자로 전달된 딕셔너리를 직접 변이하지 않고, 변경 경로에 위치한 노드만 얕은 복사(`dict(curr)`)하는 경로 기반 구조적 복사(Path-based Shallow Copy)를 수행합니다. 원본 데이터를 보존하면서 전체 깊은 복사(`deepcopy`)에 따른 메모리 복제 오버헤드를 $O(Depth)$ 수준으로 줄였습니다.
   - [`deep_merge`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L301-L342):
     새로운 빈 딕셔너리(`result: dict[Any, Any] = {}`)를 생성하여 병합 결과를 담음으로써 입력 딕셔너리의 원본 참조를 유지합니다.
   - [`Stopwatch.laps`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L65-L67):
     내부 `_laps` 리스트의 얕은 복사본(`list(self._laps)`)을 프로퍼티로 반환하여 외부에서 랩 기록을 직접 수정하거나 삭제하지 못하도록 차단했습니다.

4. **실무적 타입 결함 발견 사항 (개선 필요)**:
   - `quiver/behavior.py`의 래퍼 클래스들([`OnceWrapper`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L104), [`DebounceWrapper`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L134), [`ThrottleWrapper`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L194), [`MemoizeWrapper`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L237))이 `Generic[P, R]`을 상속하지 않고 일반 클래스로 선언되어 있습니다.
   - 이로 인해 엄격한 `mypy` 검사 시 `ParamSpec "P" is unbound` 경고가 발생합니다. 해당 래퍼 클래스들에 `Generic[P, R]` 상속을 명시해야 클래스 인스턴스 레벨에서 타입 바인딩이 성립합니다 (세부 사항은 2절 개선 제안 참조).

---

### 1.3 Pillar 3: 보안 & 방어 프로그래밍 상세 검토

1. **사전 컴파일된 정규식을 통한 ReDoS 방어**:
   - [`strings.py:L11-L20`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L11-L20)에서 사용되는 문자열 토큰화 및 마스킹 정규식 패턴 9종이 모두 모듈 로드 시점에 사전 컴파일(`re.compile`)되어 있습니다.
   - 탐욕적 중첩 수량자(`(a+)+`, `([a-zA-Z]+)*` 등 지수 백트래킹을 유발하는 구조)가 일체 포함되어 있지 않으며, 명확한 고정 자릿수(`\d{2,4}`, `\d{6}`)와 앵커(`^`, `$`)로 한정하여 $O(N)$ 선형 시간 복잡도 내 매칭이 종료됩니다.

2. **재귀 DFS 방문 집합을 통한 순환 참조 차단**:
   - [`flatten`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L73-L109):
     다차원 컬렉션 순회 시 재귀 스택 내 컨테이너 객체의 메모리 주소(`id(current)`)를 `visited_ids: set[int]`에 등록합니다. 자기 참조 리스트(`a = [1]; a.append(a)`) 인입 시 무한 재귀에 빠지지 않고 즉시 `ValueError("Circular reference detected")`를 발생시키며, `finally: visited_ids.remove(curr_id)`로 스택 복원을 보장합니다.
   - [`deep_merge`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L301-L342)에서도 동일한 `visited_ids` 메커니즘을 적용하여 딕셔너리 병합 시의 순환 참조 오버플로우를 차단했습니다.
   - 원자 타입 분해 방어: [`flatten:L84-L87`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L84-L87)에서 `str`, `bytes`, `bytearray`, `Mapping`은 이터러블이더라도 순회 대상에서 제외하여 문자 단위로 쪼개지는 파이썬 특유의 부작용을 방지했습니다.

3. **개인 식별자 및 금융 정보 표준 마스킹**:
   - [`mask_sensitive`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L117-L180):
     - **이메일**: 아이디의 첫 글자와 마지막 글자만 노출하고 중간 문자열 마스킹 (`e******r@domain.com`). 1~2글자 단축 아이디 대응 완료.
     - **전화번호**: 10~11자리 번호 및 하이픈 표기 번호에 대해 국번 중간 3~4자리 마스킹 (`010-****-5678`).
     - **주민등록번호(RRN)**: 생년월일 6자리와 성별 식별 1자리만 유지하고 뒷자리 마스킹 (`900101-1******`).
     - **신용카드**: 앞 4자리와 뒤 4자리만 유지하고 중간 8자리 마스킹 (`1234-****-****-3456`).
     - 입력값이 `None`이거나 빈 문자열일 때 크래시 없이 빈 문자열(`""`)로 우아하게 폴백 처리합니다.

4. **시스템 시그널 즉각 상위 전파 (Fail-Fast)**:
   - [`retry`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L355-L356, #L373-L374):
     동기 및 비동기 재시도 루프에서 `KeyboardInterrupt`와 `SystemExit`를 명시적으로 포착하여 재시도하지 않고 상위로 즉시 `raise`합니다. 이를 통해 터미널 인터럽트나 컨테이너 종료 시그널(SIGTERM/SIGINT) 수신 시 재시도 루프에 갇히는 결함을 방지했습니다.

---

### 1.4 Pillar 4: 성능 & 동시성 상세 검토 및 실무 트레이드오프

1. **`Stopwatch`의 나노초 단조 증가 계측 (`time.perf_counter_ns`)**:
   - [`timing.py:L73`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L73), [`L100`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L100)에서 NTP 시간 동기화나 시스템 시계 변경의 영향을 받지 않는 OS 단조 시계 `time.perf_counter_ns()`를 적용했습니다.
   - 나노초 단위 정수 연산을 사용하므로 부동소수점 누적 오차가 발생하지 않으며, `threading.Lock` 보호 하에 상태 머신(`_start_ns`, `_accumulated_ns`, `_is_running`, `_laps`)의 원자성을 보장합니다.

2. **`memoize`의 `threading.RLock` 세분도와 트레이드오프**:
   - [`behavior.py:L252`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L252)에서 일반 락 대신 재진입 가능 락(`threading.RLock`)을 채택하여 피보나치 수열 등 재귀 함수 호출 시 동일 스레드 내의 자체 데드락(Self-Deadlock)을 방어했습니다.
   - `OrderedDict`를 통한 $O(1)$ LRU 축출과 `time.monotonic()` 기반 TTL 만료 검증이 단일 락 컨텍스트 내에서 원자적으로 처리됩니다.
   - **실무 테크리드 관점의 주의점 (Lock Granularity Trade-off)**:
     - 현재 구현은 `with self._lock:` 블록 내부에서 `result = self._fn(*args, **kwargs)`를 실행합니다.
     - *장점*: 여러 스레드가 동시에 동일한 키를 요청할 때 중복 계산을 방지하는 Cache Stampede 방어 효과가 있습니다.
     - *단점*: 만약 `self._fn`이 무거운 연산이거나 외부 I/O를 수반할 경우, 한 스레드가 연산을 마칠 때까지 락을 잡고 있어 다른 스레드의 캐시 히트(Cache Hit) 조회까지 블로킹될 수 있습니다. `quiver`는 순수 CPU 인메모리 유틸리티 라이브러리이므로 현재 구현이 단순하고 안전하지만, 향후 I/O 바운드 작업에 적용할 때는 연산과 캐시 쓰기를 분리하는 이중 검사 패턴을 고려해야 합니다.

3. **`RateLimiter`의 원자적 토큰 버킷 및 논블로킹 락 릴리즈**:
   - [`timing.py:L258-L296`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L258-L296)의 [`acquire()`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L258-L297) 메서드는 `threading.Lock` 내에서 경과 시간에 따른 토큰 충전 수식($\Delta \text{tokens} = \Delta t \times \text{fill\_rate}$)을 계산하고 차감합니다.
   - 가용 토큰 부족 시 대기(`blocking=True`) 처리에서 **락을 잡은 채로 슬립하지 않고**, 대기 시간만 산출한 후 락을 해제하고 `time.sleep(min(sleep_duration, 0.05))`을 수행합니다. 이를 통해 다른 스레드가 토큰을 조회하거나 차감할 수 있는 기회를 보장하여 락 경합 병목을 효과적으로 완화했습니다.

4. **`once`의 Double-Checked Locking 패턴**:
   - [`behavior.py:L114-L120`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L114-L120)에서 `if not self._has_run:` 1차 검사 후 락을 획득하고 다시 `if not self._has_run:`을 검사합니다. 초기 1회 실행 후에는 락 획득 오버헤드 없이 즉시 캐시된 결과를 반환합니다.
   - 1차 실행 중 예외 발생 시 `self._has_run`을 `True`로 전환하지 않아, 일시적 장애 복구 후 재호출 기회를 제공합니다.

5. **제너레이터 스트리밍 소비 시 주의사항**:
   - [`chunk`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L20-L71) 및 [`windowed`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L196-L225)는 `itertools.islice`와 `yield`를 활용하여 $O(size)$의 최소 메모리만 사용합니다.
   - **호출부 주의사항**: 파이썬 제너레이터 특성상 **한 번 순회하면 소진(Exhausted)**됩니다. 따라서 결과를 다회 순회하거나 인덱싱해야 하는 호출부에서는 `list(chunk(...))`로 명시적 구체화를 해야 하며, 제너레이터가 입력으로 인입될 경우 원본 제너레이터 역시 소비된다는 점을 개발 가이드에 명시할 필요가 있습니다.

---

### 1.5 Pillar 5: 테스트 품질 & 커버리지 상세 검토

1. **테스트 전수 통과**:
   - 6개 테스트 모듈에서 작성된 총 194개 테스트가 0.98초 만에 에러나 실패 없이 통과했습니다:
     - [`test_collections.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests/test_collections.py): 67 passed
     - [`test_behavior.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests/test_behavior.py): 35 passed
     - [`test_strings.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests/test_strings.py): 49 passed
     - [`test_scope.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests/test_scope.py): 16 passed
     - [`test_timing.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests/test_timing.py): 22 passed
     - [`test_concurrency.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests/test_concurrency.py): 6 passed

2. **라인 커버리지 99% 달성**:
   - 전체 788문장 중 782문장이 실행되어 **99% 라인 커버리지**를 달성했습니다.
   - 미실행 구문 6개는 `quiver/behavior.py` 내 `retry`의 최대 재시도 초과 후 최하단 방어선 구문(`raise RuntimeError("Exhausted retries")`) 및 코루틴 폴백 경로로, 실제 장애 시나리오에서는 상위 예외가 먼저 재발생(Re-raise)하도록 의도된 방어 코드입니다.

3. **100 스레드 동시성 스트레스 검증 ([`tests/test_concurrency.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/tests/test_concurrency.py))**:
   - `threading.Barrier(100)`를 투입하여 100개 스레드가 정밀하게 동일 순간에 경합하도록 유도했습니다:
     - `test_100_threads_once_guarantee`: 100개 스레드가 동시 초기화 진입 시 정확히 1회만 초기화가 수행되고 동일 결과를 공유함을 검증했습니다.
     - `test_100_threads_memoize_no_deadlock`: 100개 스레드가 50개 용량의 LRU 캐시에 동시 접근 시 교착상태(Deadlock) 없이 완료됨을 확인했습니다.
     - `test_100_threads_rate_limiter_atomic_consumption`: 10개 용량의 토큰 버킷에 대해 100개 스레드가 동시 비블로킹 획득 시 정확히 10개만 통과하고 90개는 거절되어 원자적 토큰 차감을 입증했습니다.
     - `test_100_threads_stopwatch_laps`: 100개 스레드가 동시 `lap()` 기록 시 0부터 99까지의 인덱스가 누락 없이 순차 기록됨을 확인했습니다.

---

## 2. 세부 피드백 및 코드 개선 제안 (Action Items)

### [개선 권장 / 정적 타입 안정성] `quiver.behavior` 내 래퍼 클래스에 `Generic[P, R]` 상속 선언
- **위치**: [`quiver/behavior.py:L104`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L104), [`L134`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L134), [`L194`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L194), [`L237`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L237)
- **발견 사항**:
  - `OnceWrapper`, `DebounceWrapper`, `ThrottleWrapper`, `MemoizeWrapper` 클래스 선언부에 `Generic[P, R]`이 상속되어 있지 않습니다.
  - 이로 인해 `mypy` 검사 시 클래스 내부의 `P`와 `R`이 바인딩되지 않아 `ParamSpec "P" is unbound` 에러가 발생합니다.
- **개선 제안 (Diff)**:
```python
<<<<
from typing import (
    Any,
    Callable,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    overload,
)

P = ParamSpec("P")
R = TypeVar("R")


class OnceWrapper:
    """Wrapper ensuring a callable runs at most once in a multi-threaded environment."""

    def __init__(self, fn: Callable[P, R]) -> None:
====
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    overload,
)

P = ParamSpec("P")
R = TypeVar("R")


class OnceWrapper(Generic[P, R]):
    """Wrapper ensuring a callable runs at most once in a multi-threaded environment."""

    def __init__(self, fn: Callable[P, R]) -> None:
>>>>
```
```python
<<<<
class DebounceWrapper:
    """Wrapper delaying execution until a period of silence has elapsed."""

    def __init__(self, fn: Callable[P, R], wait_seconds: float) -> None:
====
class DebounceWrapper(Generic[P, R]):
    """Wrapper delaying execution until a period of silence has elapsed."""

    def __init__(self, fn: Callable[P, R], wait_seconds: float) -> None:
>>>>
```
```python
<<<<
class ThrottleWrapper:
    """Wrapper restricting execution frequency to at most once per interval."""

    def __init__(self, fn: Callable[P, R], interval_seconds: float) -> None:
====
class ThrottleWrapper(Generic[P, R]):
    """Wrapper restricting execution frequency to at most once per interval."""

    def __init__(self, fn: Callable[P, R], interval_seconds: float) -> None:
>>>>
```
```python
<<<<
class MemoizeWrapper:
    """Thread-safe memoization wrapper supporting TTL and LRU cache eviction."""

    def __init__(
        self,
        fn: Callable[P, R],
        ttl_seconds: Optional[float],
        maxsize: Optional[int],
        key_fn: Optional[Callable[..., Any]],
    ) -> None:
====
class MemoizeWrapper(Generic[P, R]):
    """Thread-safe memoization wrapper supporting TTL and LRU cache eviction."""

    def __init__(
        self,
        fn: Callable[P, R],
        ttl_seconds: Optional[float],
        maxsize: Optional[int],
        key_fn: Optional[Callable[..., Any]],
    ) -> None:
>>>>
```

---

### [개선 권장 / DX & 일관성] `RateLimiter`에 `async with` 비동기 컨텍스트 매니저 프로토콜 추가
- **위치**: [`quiver/timing.py:L298-L302`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L298-L302)
- **발견 사항**:
  - `RateLimiter`는 동기 컨텍스트 매니저(`__enter__`, `__exit__`) 및 동기/비동기 함수 데코레이터를 모두 지원하지만, 정작 비동기 블록에서 사용할 `async with limiter:` 구문 프로토콜(`__aenter__`, `__aexit__`)이 빠져 있습니다.
- **개선 제안 (Diff)**:
```python
<<<<
    def __enter__(self) -> bool:
        return self.acquire(tokens=1.0, blocking=True)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass
====
    def __enter__(self) -> bool:
        return self.acquire(tokens=1.0, blocking=True)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def __aenter__(self) -> bool:
        return self.acquire(tokens=1.0, blocking=True)

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass
>>>>
```

---

### [개선 권장 / 정적 타입 안정성] `quiver.collections`의 `deep_get` / `deep_set` 타입 불변성(Invariance) 보정
- **위치**: [`quiver/collections.py:L239-L241`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L239-L241), [`L281-L298`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L281-L298), [`L329`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L329)
- **발견 사항**:
  - 파이썬에서 `list`는 불변(Invariant) 타입이므로 `path.split(separator)`의 반환형 `list[str]`을 `keys: list[Union[str, int]]`에 대입하면 타입 불일치 경고가 보고됩니다.
  - 공변(Covariant) 인터페이스인 `Sequence[Union[str, int]]`를 활용하고 `sub = {}`에 명시적 타입 어노테이션을 부여하여 해결할 수 있습니다.
- **개선 제안 (Diff)**:
```python
<<<<
    if isinstance(path, str):
        keys: list[Union[str, int]] = path.split(separator)
    else:
        keys = list(path)
====
    keys: Sequence[Union[str, int]]
    if isinstance(path, str):
        keys = path.split(separator)
    else:
        keys = list(path)
>>>>
```
```python
<<<<
                elif isinstance(v, Mapping):
                    sub = {}
                    _merge_into(sub, v)
                    target[k] = sub
====
                elif isinstance(v, Mapping):
                    sub: dict[Any, Any] = {}
                    _merge_into(sub, v)
                    target[k] = sub
>>>>
```

---

## 3. 최종 리뷰 판정 및 출시 승인

- **판정 결과**: **APPROVED (승인)**
- **승인 코멘트**: 
  - 외부 런타임 의존성 0개(`dependencies = []`) 원칙이 엄격히 지켜졌으며, 5대 도메인 모듈 간 결합도가 낮아 유지보수성이 높습니다.
  - Copy-on-Write 불변성, 사전 컴파일 정규식, 순환 참조 가드, 나노초 단조 시계, 토큰 버킷 락 해제 후 슬립 패턴 등 실무 엔지니어링 완성도가 검증되었습니다.
  - 총 194개 단위 테스트 전수 통과, 99% 라인 커버리지, 100 스레드 동시성 스트레스 검증을 완료했습니다.
  - 지적된 래퍼 클래스의 `Generic[P, R]` 선언과 `async with` 지원 등 권장 사항은 마이너 패치 단계에서 반영 가능한 수준이므로, 본 패키지의 Stage 5(배포 명세 및 패키징) 단계 진입을 승인합니다.
