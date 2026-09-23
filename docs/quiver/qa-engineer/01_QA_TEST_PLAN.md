# [quiver] 통합 QA 테스트 계획서 (QA Test Plan)

- **작성일자**: 2026-09-23
- **작성자**: 수석 품질 보증 엔지니어 (`qa-engineer`)
- **문서 버전**: v1.0
- **상태**: **Approved**

---

## 1. 테스트 범위 및 환경 (Test Scope & Environment)

### 1.1 테스트 대상 및 목적
본 계획서는 `quiver` v0.1.0 패키지의 5대 코어 모듈과 고동시성 환경에서의 동작 무결성을 사전 검증하기 위한 테스트 전략과 시나리오를 정의합니다. 외부 서드파티 의존성이 전혀 없는 Zero-Dependency 순수 파이썬 라이브러리 특성상, 외부 I/O 모킹보다는 파이썬 내장 동시성 원시 타입(`threading.Lock`, `RLock`, `Barrier`), 메모리 참조 추적(순환 참조 차단), 정규식 백트래킹(ReDoS) 방어 등 런타임 안정성 검증에 집중합니다.

- **기획 및 설계 정합성 기준**:
  - 제품 요구사항 정의서 ([`01_PRD.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/spec-writer/01_PRD.md))
  - 상세 기능 정의서 ([`02_FUNCTIONAL_SPECIFICATION.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/spec-writer/02_FUNCTIONAL_SPECIFICATION.md))
  - 정책 및 엣지 케이스 정의서 ([`03_POLICIES_AND_EDGES.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/spec-writer/03_POLICIES_AND_EDGES.md))
  - 시스템 설계 명세서 ([`01_SYSTEM_DESIGN.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/system-designer/01_SYSTEM_DESIGN.md))
  - 아키텍처 결정 레코드 ([`01_ARCHITECTURE_ADR.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/fullstack-architect/01_ARCHITECTURE_ADR.md))
  - 백엔드 TDD 사이클 기록서 ([`01_TDD_CYCLE_LOG.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/backend-tdd-engineer/01_TDD_CYCLE_LOG.md))
  - 코드 품질 감사 보고서 ([`01_CODE_REVIEW_REPORT.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/backend-code-reviewer/01_CODE_REVIEW_REPORT.md))

- **대상 5대 모듈 및 핵심 기술적 리스크 요인**:
  1. [`quiver.collections`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py) (13종):
     - 핵심 심볼: [`chunk`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L20), [`flatten`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L73), [`group_by`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L112), [`key_by`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L134), [`partition`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L152), [`uniq_by`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L170), [`windowed`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L196), [`deep_get`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L227), [`deep_set`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L267), [`deep_merge`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L301), [`pick`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L344), [`omit`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L349), [`invert`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L355)
     - QA 중점: `flatten` 및 `deep_merge`에서의 순환 참조(Self-referential Container) 감지 및 OOM 방지, `deep_set`의 원본 불변(Copy-on-Write) 보장.
  2. [`quiver.behavior`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py) (8종):
     - 핵심 심볼: [`pipe`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L27), [`compose`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L40), [`curry`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L61), [`once`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L129), [`debounce`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L183), [`throttle`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L218), [`memoize`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L313), [`retry`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L326)
     - QA 중점: `memoize`의 재귀 호출 시 데드락 방지(`threading.RLock`), `retry`의 AWS Full Jitter 지수 백오프 및 시스템 시그널(`KeyboardInterrupt`, `SystemExit`) 상위 전파 보장.
  3. [`quiver.strings`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py) (7종):
     - 핵심 심볼: [`to_camel_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L32), [`to_snake_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L40), [`to_kebab_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L46), [`to_pascal_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L52), [`slugify`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L58), [`truncate`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L83), [`mask_sensitive`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L117)
     - QA 중점: 대용량 문자열 및 반복 패턴 입력 시의 ReDoS(Catastrophic Backtracking) 차단, PII 식별자 마스킹 마진 무결성.
  4. [`quiver.scope`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py) (6종):
     - 핵심 심볼: [`let`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L12), [`also`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L19), [`tap`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L27), [`take_if`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L32), [`take_unless`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L39), [`coalesce`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L46)
     - QA 중점: 체이닝 과정에서 `None`과 Falsy 값(`0`, `""`, `False`) 간의 구분 보존.
  5. [`quiver.timing`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py) (3종):
     - 핵심 심볼: [`Stopwatch`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L37), [`measure_time`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L202), [`RateLimiter`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L210)
     - QA 중점: `time.perf_counter_ns` 기반 단조 시계 계측, 100개 스레드 동시 진입 시 토큰 버킷 원자적 소비 및 대기 스레드 간 블로킹 병목 격리.
  6. 최상위 패키지 진입점: [`quiver/__init__.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/__init__.py) 및 타입 마커 [`quiver/py.typed`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/py.typed)

### 1.2 테스트 환경 구성 및 제약 조건
- **런타임 및 OS 환경**:
  - Python 버전: `3.11.9` (호환성 검증 대상: `3.10 ~ 3.13`)
  - 운영체제: macOS (darwin arm64) 및 Linux (Ubuntu 22.04 LTS x86_64)
- **외부 의존성 제약**:
  - 런타임 의존성 0개 (`dependencies = []`). 서드파티 패키지 임포트가 단 하나라도 발생하면 즉시 빌드 실패 처리.
- **테스트 및 계측 도구**:
  - `pytest 9.1.1`, `pytest-asyncio 1.4.0`, `pytest-cov 7.1.0`
- **동시성 부하 인프라**:
  - `concurrent.futures.ThreadPoolExecutor` (100 워커 스레드 동시 실행)
  - `threading.Barrier(100)`: 100개 스레드가 동시에 실행을 시작하도록 동기화 지점을 설정하여 순간 경합(Thundering Herd)을 유발.
- **실무 주의사항 및 트레이드오프 (Gotchas)**:
  - `deep_set`과 `deep_merge`는 원본 변형을 방지하기 위해 Copy-on-Write 방식으로 경로를 복제합니다. 중첩 깊이가 10단계 이상이거나 10만 건 이상의 대형 딕셔너리에서는 복사 비용(메모리 할당 O(N))이 발생하므로 성능 임계 경로에서는 배치 처리가 권장됩니다.
  - `RateLimiter`는 락 내부에서 슬립하지 않고 대기 시간을 계산한 뒤 락을 풀고 `time.sleep`을 수행합니다. 스레드 풀 정체는 방지되지만, OS 스케줄링 특성상 마이크로초 단위의 타이밍 오차가 발생할 수 있습니다.

---

## 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 케이스 ID | 테스트 구분 | 검증 시나리오 | 사전 조건 및 입력 데이터 | 기대 결과 (Pass Criteria) |
| :--- | :---: | :--- | :--- | :--- |
| **`TC-COLL-001`** | **컬렉션 핵심 & 불변성** | **`collections` 핵심 함수 (`chunk`, `flatten`, `group_by`, `deep_get`/`set`, `deep_merge`) 불변성 및 순환참조 방어 검증** | - 리스트, 제너레이터, 다계층 딕셔너리<br>- 순환 참조 리스트: `a = [1]; a.append(a)`<br>- 순환 참조 딕셔너리: `d = {}; d["self"] = d`<br>- `deep_set` / `deep_merge` 원본 딕셔너리 | - `chunk`: 균등 분할 및 제너레이터 스트리밍 정상 완료, `size < 1` 시 `ValueError` 발생.<br>- `flatten`: 임의 깊이 평탄화 지원, 문자열/바이트 원자 타입 보존, 순환 참조 감지 시 즉각 `ValueError` 차단.<br>- `group_by`: 키 추출 함수 기준 딕셔너리 그룹화 및 순서 유지.<br>- `deep_get`/`set`: 점 표기법/리스트 경로 탐색, `deep_set` 적용 후에도 원본 딕셔너리가 변경되지 않음(Copy-on-Write).<br>- `deep_merge`: 중첩 딕셔너리 재귀 병합, 원본 불변, 순환 참조 감지 시 `ValueError` 발생. |
| `TC-COLL-002` | 컬렉션 확장 유틸 | `key_by`, `partition`, `uniq_by`, `windowed`, `pick`, `omit`, `invert` 기능 및 엣지 케이스 검증 | - 단일 키 추출 함수, 참/거짓 분리 조건자, 슬라이딩 윈도우 크기/보폭, 역전 키-값 쌍 | - `key_by`: 키 기준 단일 매핑 (중복 키는 후속 값 덮어쓰기).<br>- `partition`: 조건 만족/불만족 리스트 2개 튜플로 정확히 분할.<br>- `uniq_by`: 순서 보존 고유화 (Unhashable 객체는 O(N²) 비교 폴백 동작).<br>- `windowed`: 슬라이딩 윈도우 생성 및 `fill_value` 패딩 정상 동작.<br>- `pick`/`omit`: 지정 키 포함/제외 필터링 정상 완료.<br>- `invert`: 단일 매핑 및 `multi=True` 시 리스트 그룹화 역전 지원. |
| **`TC-BEHV-001`** | **고차 함수 & 회복성** | **`behavior` 모듈 (`pipe`, `compose`, `memoize` TTL/LRU, `retry` Full Jitter) 실행 및 예외 회복력 검증** | - 다단계 파이프라인 함수열<br>- TTL(초) 및 LRU 용량 제한 캐시 함수<br>- 재시도 실패 시뮬레이션 함수 (동기 및 비동기 `async def`), 시스템 시그널 주입 | - `pipe`: 왼쪽에서 오른쪽으로 인자 순차 전달 및 결과 반환.<br>- `compose`: 오른쪽에서 왼쪽으로 함수 합성 실행.<br>- `memoize`: LRU `maxsize` 초과 시 오래된 항목 축출, `ttl` 만료 시 재계산, 재진입 락(`threading.RLock`)으로 재귀 호출 데드락 방지.<br>- `retry`: AWS Full Jitter 지수 백오프 공식 준수, 재시도 횟수 초과 시 원인 예외 방출, `KeyboardInterrupt`/`SystemExit` 발생 시 재시도 없이 상위 전파. |
| `TC-BEHV-002` | 함수 실행 제어 | `curry`, `once`, `debounce`, `throttle` 호출 제어 및 스레드 타이머 검증 | - 가변/고정 인자 함수, 단 1회 실행 함수, 타이머 기반 디바운스/스로틀 함수 | - `curry`: 인자 수 충족 전까지 부분 적용 함수 반환, 충족 시 최종 실행.<br>- `once`: 다중 호출 시에도 최초 1회만 본문 실행되고 캐시된 결과 반환, `reset()` 시 재실행 허용.<br>- `debounce`: 마지막 호출 후 대기 시간 경과 시 1회 실행, `cancel()` 및 `flush()` 정상 동작.<br>- `throttle`: 지정 시간 주기 내 최초 호출만 실행하고 후속 호출 무시. |
| **`TC-STR-001`** | **문자열 변환 & 보안** | **`strings` 모듈 케이스 변환 4종, `slugify`, `truncate`, `mask_sensitive` 개인정보 마스킹 검증** | - 혼합 표기법 문자열(Camel, Snake, Kebab, Pascal)<br>- 유니코드(한글, 악센트) 슬러그 대상<br>- 이메일, 전화번호, 주민등록번호, 신용카드 번호 테스트 문자열 | - 케이스 4종: 상호 변환 시 단어 경계 보존 및 무결성 유지.<br>- `slugify`: NFKD 정규화 및 유니코드/ASCII 모드 지원, 연속 구분자 제거.<br>- `truncate`: 길이 제한 초과 시 말줄임표 처리 및 단어 경계(`preserve_words=True`) 보존.<br>- `mask_sensitive`: ReDoS 방어 사전 컴파일 정규식 기반으로 이메일, 전화번호, 주민번호(앞 6자리+뒤 1자리 노출 후 마스킹), 카드번호(앞 6자리+뒤 4자리 노출 후 마스킹) 정확 마스킹. |
| **`TC-SCP-001`** | **스코프 & 널 안전** | **`scope` 모듈 (`let`, `also`, `take_if`, `coalesce`) 체이닝 및 널 안전 검증** | - 임의의 파이썬 객체, 람다 변환식, 로깅 콜백, `None` 및 Falsy(`0`, `""`, `[]`) 인자열 | - `let`: 대상 객체를 람다에 전달하여 변환 결과 반환 (`None` 안전 호출 지원).<br>- `also`/`tap`: 부수 효과 함수를 실행하고 대상 객체 자신을 그대로 반환.<br>- `take_if`/`take_unless`: 조건자 일치 여부에 따라 대상 객체 또는 `None` 반환.<br>- `coalesce`: 전달된 인자 중 최초의 `non-None` 값을 반환하며, Falsy 값(`0`, `""`, `False`)은 온전히 보존. |
| **`TC-TIME-001`** | **정밀 시간 & 속도 제한** | **`timing` 모듈 (`Stopwatch` 나노초 단조시계, `measure_time`, `RateLimiter` 토큰버킷) 검증** | - 구간 랩 타임 기록, 동기/비동기 함수 실행 시간 계측, 초당 허용 요청량 및 버스트 설정 | - `Stopwatch`: `time.perf_counter_ns` 기반 고정밀 나노초 계측, 시작/일시정지/재개/리셋/랩 레코드(`LapRecord`) 불변 반환.<br>- `measure_time`: 컨텍스트 매니저 및 동기/비동기 데코레이터 지원, 시간 단위(`ns`, `us`, `ms`, `s`) 변환 및 콜백 연동.<br>- `RateLimiter`: 토큰 버킷 알고리즘 기반 토큰 획득(`acquire`), 버스트 용량 준수, 비차단 모드 및 타임아웃 차단 대기 정상 작동. |
| **`TC-CONC-001`** | **100 스레드 동시성 스트레스** | **100 스레드 동시 진입 멀티스레드 스트레스 및 경합 무결성 검증** | - `ThreadPoolExecutor(max_workers=100)`<br>- `threading.Barrier(100)`를 통한 100개 스레드 동시 릴리즈<br>- 대상: `once`, `memoize`, `RateLimiter`, `Stopwatch` | - `once`: 100개 스레드가 동시 진입해도 초기화 함수는 정확히 1회만 실행되며 100개 스레드 모두 동일 인스턴스/결과 수신.<br>- `memoize`: 100개 스레드가 동시 다발적으로 동일 키/서로 다른 키를 요청할 때 락 경합 및 데드락 없이 안정적으로 캐시 반환.<br>- `RateLimiter`: 버스트 크기 10으로 설정 시 100개 동시 비차단 요청 중 정확히 10건만 성공(`True`)하고 90건은 즉시 거절(`False`). 잔여 토큰 음수 강하 없음.<br>- `Stopwatch`: 100개 스레드가 동시에 `sw.lap()` 호출 시 누락 없이 정확히 100개의 인덱스(0~99) 순차 할당 및 무결성 유지. |
| `TC-PKG-001` | 패키징 & 타입 마커 | `__all__` 선언 무결성 및 PEP 561 마커 파일 검증 | - 최상위 진입점 `quiver` 모듈 임포트<br>- 배포 패키지 내 `quiver/py.typed` 파일 존재 여부 | - `quiver.__all__`에 35개 공개 유틸리티 심볼이 누락 없이 정의되어 있으며, 최상위 네임스페이스에서 직접 임포트 가능.<br>- `quiver/py.typed` 파일이 존재하여 다운스트림의 `mypy --strict` 및 IDE 정적 분석기에서 인라인 타입 힌트 완전 인식. |
