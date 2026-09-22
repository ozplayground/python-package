# [quiver] 통합 QA 테스트 계획서 (QA Test Plan)

- **작성일자**: 2026-09-23
- **작성자**: 수석 품질 보증 엔지니어 (`qa-engineer`)
- **문서 버전**: v1.0
- **상태**: **Approved**

---

## 1. 테스트 범위 및 환경 (Test Scope & Environment)

### 1.1 테스트 대상 및 목적
본 테스트 계획서는 파이썬 엔지니어링 생태계를 위한 모던, 제로 의존성(Zero-Dependency), 완전 정적 타입 안정성 유틸리티 패키지인 `quiver`의 전 기능 및 비기능(동시성, 회복성, 경합 무결성) 요구사항을 전수 검증하기 위해 수립되었습니다.
- **기획 및 아키텍처 정합성 검증 기준**:
  - 기획 요구사항 정의서 ([`01_PRD.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/spec-writer/01_PRD.md))
  - 상세 기능 정의서 ([`02_FUNCTIONAL_SPECIFICATION.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/spec-writer/02_FUNCTIONAL_SPECIFICATION.md))
  - 예외 및 엣지 정책서 ([`03_POLICIES_AND_EDGES.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/spec-writer/03_POLICIES_AND_EDGES.md))
  - 시스템 설계 명세서 ([`01_SYSTEM_DESIGN.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/system-designer/01_SYSTEM_DESIGN.md))
  - 아키텍처 결정 레코드 ([`01_ARCHITECTURE_ADR.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/fullstack-architect/01_ARCHITECTURE_ADR.md))
  - 백엔드 TDD 사이클 기록서 ([`01_TDD_CYCLE_LOG.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/backend-tdd-engineer/01_TDD_CYCLE_LOG.md))
  - 5-Pillar 코드 품질 감사 보고서 ([`01_CODE_REVIEW_REPORT.md`](file:///Users/wonyoung/workspace/ozplayground/python-package/docs/quiver/backend-code-reviewer/01_CODE_REVIEW_REPORT.md))
- **대상 핵심 도메인 5대 모듈**:
  1. [`quiver.collections`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py): 불변 컬렉션 조작 13종 ([`chunk`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L20), [`flatten`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L73), [`group_by`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L112), [`key_by`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L134), [`partition`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L152), [`uniq_by`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L170), [`windowed`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L196), [`deep_get`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L227), [`deep_set`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L267), [`deep_merge`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L301), [`pick`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L344), [`omit`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L349), [`invert`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/collections.py#L355))
  2. [`quiver.behavior`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py): 함수 제어 및 실행 8종 ([`pipe`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L27), [`compose`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L40), [`curry`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L61), [`once`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L129), [`debounce`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L183), [`throttle`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L218), [`memoize`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L313), [`retry`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/behavior.py#L326))
  3. [`quiver.strings`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py): 문자열 케이스 변환 및 보안 7종 ([`to_camel_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L32), [`to_snake_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L40), [`to_kebab_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L46), [`to_pascal_case`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L52), [`slugify`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L58), [`truncate`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L83), [`mask_sensitive`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/strings.py#L117))
  4. [`quiver.scope`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py): 스코프 함수 및 널 안전 6종 ([`let`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L12), [`also`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L19), [`tap`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L27), [`take_if`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L32), [`take_unless`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L39), [`coalesce`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/scope.py#L46))
  5. [`quiver.timing`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py): 고정밀 시간 및 속도 제어 3종 ([`Stopwatch`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L37), [`measure_time`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L202), [`RateLimiter`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/timing.py#L210))
  6. 패키지 진입점 및 PEP 561 마커: [`quiver/__init__.py`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/__init__.py), [`quiver/py.typed`](file:///Users/wonyoung/workspace/ozplayground/python-package/quiver/quiver/py.typed)

### 1.2 테스트 환경
- **런타임 및 OS 플랫폼**:
  - Python: `3.11.9` (타깃 호환성 보장: `Python 3.10, 3.11, 3.12, 3.13`)
  - 운영체제: macOS (darwin arm64) 및 Linux (Ubuntu 22.04 LTS x86_64) 크로스 플랫폼 검증
- **제로 의존성 (Zero-Dependency) 원칙**:
  - 런타임 외부 종속성 0개 (`dependencies = []`), 오직 Python 내장 표준 라이브러리(`collections`, `itertools`, `functools`, `threading`, `time`, `re`, `unicodedata`, `inspect`, `random`, `dataclasses`)만 사용
- **품질 보증 및 테스트 툴체인**:
  - 테스트 프레임워크: `pytest >= 9.1.1`
  - 비동기 테스트 러너: `pytest-asyncio >= 1.4.0` (auto 모드)
  - 커버리지 분석: `pytest-cov >= 7.1.0` (목표 커버리지 >= 95%, 허용 누락: 데코레이터 방어선)
- **동시성 및 스트레스 환경**:
  - 멀티스레드 인프라: `concurrent.futures.ThreadPoolExecutor` (100 동시 워커 스레드)
  - 동기화 메커니즘: `threading.Barrier(100)` 기반 100개 스레드 동시 발화(Thunder-herd) 경합 검증
  - 원자성 보장: `threading.Lock`, `threading.RLock` 기반의 임계 구역 및 재귀 호출 데드락 방지 검증

---

## 2. 테스트 시나리오 매트릭스 (Test Matrix)

| 케이스 ID | 테스트 구분 | 검증 시나리오 | 사전 조건 및 입력 데이터 | 기대 결과 (Pass Criteria) |
| :--- | :---: | :--- | :--- | :--- |
| **`TC-COLL-001`** | **컬렉션 핵심 & 불변성** | **`collections` 모듈 핵심 기능 (`chunk`, `flatten`, `group_by`, `deep_get`/`set`, `deep_merge`) 불변성 및 순환참조 방어 검증** | - 리스트, 제너레이터, 중첩 딕셔너리 데이터 준비<br>- 순환 참조 리스트 `a = [1]; a.append(a)` 및 딕셔너리 `d = {}; d["self"] = d`<br>- `deep_set` 및 `deep_merge` 대상 원본 딕셔너리 | - `chunk`: 균등 분할 및 제너레이터 정상 스트리밍, `size < 1` 시 `ValueError`<br>- `flatten`: 임의 깊이 평탄화 정상, 문자열/바이트 원자 타입 보존, 순환 참조 감지 시 즉각 `ValueError` 차단<br>- `group_by`: 키 추출 함수 기준 그룹화 및 순서 보존<br>- `deep_get`/`set`: 점 표기법 및 리스트 경로 지원, `deep_set` 시 원본 딕셔너리 불변(Copy-on-Write) 보장<br>- `deep_merge`: 중첩 딕셔너리 재귀 병합, 원본 불변, 순환 참조 시 `ValueError` 차단 |
| `TC-COLL-002` | 컬렉션 확장 유틸 | `key_by`, `partition`, `uniq_by`, `windowed`, `pick`, `omit`, `invert` 기능 및 엣지 케이스 검증 | - 단일 키 매핑, 참/거짓 분류 조건자, 슬라이딩 윈도우 크기/보폭, 역전 키-값 쌍 | - `key_by`: 키 기준 단일 매핑 (중복 시 마지막 값 덮어쓰기)<br>- `partition`: 조건을 만족하는 리스트와 만족하지 않는 리스트 2개 튜플로 분할<br>- `uniq_by`: 순서 보존 및 고유화 (Unhashable 원소 지원 폴백)<br>- `windowed`: 슬라이딩 윈도우 생성 및 `fill_value` 패딩 정상 동작<br>- `pick`/`omit`: 지정 키 포함/제외 필터링 완벽 동작<br>- `invert`: 단일 매핑 및 `multi=True` 시 리스트 그룹화 역전 지원 |
| **`TC-BEHV-001`** | **고차 함수 & 회복성** | **`behavior` 모듈 (`pipe`, `compose`, `memoize` TTL/LRU, `retry` Full Jitter) 실행 및 예외 회복력 검증** | - 다단계 변환 파이프라인 함수열<br>- TTL 및 LRU 용량 제한 캐시 함수<br>- 재시도 실패 시뮬레이션 함수 (동기 및 비동기 `async def`), 시스템 종료 시그널 주입 | - `pipe`: 왼쪽에서 오른쪽으로 인자 순차 전달 및 최종 결과 반환<br>- `compose`: 오른쪽에서 왼쪽으로 수학적 함수 합성 수행<br>- `memoize`: LRU `maxsize` 초과 시 오래된 키 축출, `ttl` 만료 시 재계산, `RLock` 적용으로 재귀 호출 데드락 방지<br>- `retry`: AWS Full Jitter 지수 백오프 공식 적용, 재시도 상한 도달 시 원인 예외 방출, `KeyboardInterrupt`/`SystemExit` 발생 시 재시도 없이 상위 전파 |
| `TC-BEHV-002` | 함수 실행 제어 | `curry`, `once`, `debounce`, `throttle` 호출 제어 및 스레드 타이머 검증 | - 가변/고정 인자 함수, 단 1회 실행 함수, 타이머 기반 디바운스/스로틀 함수 | - `curry`: 인자 수 충족 전까지 부분 적용 함수 반환, 충족 시 최종 실행<br>- `once`: 다중 호출 시에도 최초 1회만 본문 실행되고 결과 캐싱 반환, `reset()` 시 재실행 허용<br>- `debounce`: 마지막 호출 후 대기 시간 경과 시 1회 실행, `cancel()` 및 `flush()` 정상 동작<br>- `throttle`: 지정 시간 주기 내 최초 호출만 실행하고 후속 호출 무시 |
| **`TC-STR-001`** | **문자열 변환 & 보안** | **`strings` 모듈 케이스 변환 4종, `slugify`, `truncate`, `mask_sensitive` 개인정보 마스킹 검증** | - 혼합 표기법 문자열(Camel, Snake, Kebab, Pascal, 공백, 특수문자)<br>- 유니코드(한글, 악센트) 슬러그 대상<br>- 이메일, 전화번호, 주민등록번호, 신용카드 번호 테스트 문자열 | - 케이스 4종: `to_camel_case`, `to_snake_case`, `to_kebab_case`, `to_pascal_case` 간 상호 변환 100% 무결성<br>- `slugify`: NFKD 정규화 및 유니코드/ASCII 모드 지원, 연속 구분자 제거<br>- `truncate`: 길이 제한 초과 시 말줄임표 처리 및 단어 경계(`preserve_words=True`) 보존<br>- `mask_sensitive`: ReDoS 방어 컴파일 정규식 기반으로 이메일, 전화번호, 주민번호(앞 6자리+뒤 1자리 노출 후 마스킹), 카드번호(앞 6자리+뒤 4자리 노출 후 마스킹) 정확 마스킹 |
| **`TC-SCP-001`** | **스코프 & 널 안전** | **`scope` 모듈 (`let`, `also`, `take_if`, `coalesce`) 체이닝 및 널 안전 검증** | - 임의의 파이썬 객체, 람다 변환식, 부수 효과 로깅 콜백, `None` 및 다양한 Falsy(`0`, `""`, `[]`) 인자열 | - `let`: 대상 객체를 람다에 전달하여 변환 결과 반환 (`None` 안전 호출 지원)<br>- `also`/`tap`: 부수 효과 함수를 실행하고 대상 객체 자신을 그대로 반환<br>- `take_if`/`take_unless`: 조건자 일치 여부에 따라 대상 객체 또는 `None` 반환<br>- `coalesce`: 전달된 인자 중 최초의 `non-None` 값을 반환하며, Falsy 값(`0`, `""`, `False`)은 온전히 보존 |
| **`TC-TIME-001`** | **정밀 시간 & 속도 제한** | **`timing` 모듈 (`Stopwatch` 나노초 단조시계, `measure_time`, `RateLimiter` 토큰버킷) 검증** | - 구간 랩 타임 기록, 동기/비동기 함수 실행 시간 계측, 초당 허용 요청량 및 버스트 설정 | - `Stopwatch`: `time.perf_counter_ns` 기반 고정밀 나노초 계측, 시작/일시정지/재개/리셋/랩 레코드(`LapRecord`) 불변 데이터 반환<br>- `measure_time`: 컨텍스트 매니저 및 동기/비동기 데코레이터 지원, 시간 단위(`ns`, `us`, `ms`, `s`) 정밀 변환 및 콜백 연동<br>- `RateLimiter`: 토큰 버킷 알고리즘 기반 토큰 획득(`acquire`), 버스트 용량 준수, 비차단 모드 및 타임아웃 차단 대기 정상 작동 |
| **`TC-CONC-001`** | **100 스레드 동시성 스트레스** | **100 스레드 동시 진입 멀티스레드 스트레스 및 경합 무결성 검증** | - `ThreadPoolExecutor(max_workers=100)`<br>- `threading.Barrier(100)`를 통한 100개 스레드 동시 릴리즈<br>- 대상: `once`, `memoize`, `RateLimiter`, `Stopwatch` | - `once`: 100개 스레드가 동시 진입해도 초기화 함수는 정확히 1회만 실행되며 100개 스레드 모두 동일 인스턴스/결과 수신<br>- `memoize`: 100개 스레드가 동시 다발적으로 동일 키/서로 다른 키를 요청할 때 락 경합 및 데드락 없이 안정적으로 캐시 반환<br>- `RateLimiter`: 버스트 크기 10으로 설정 시 100개 동시 비차단 요청 중 정확히 10건만 성공(`True`)하고 90건은 즉시 거절(`False`)<br>- `Stopwatch`: 100개 스레드가 동시에 `sw.lap()` 호출 시 누락 없이 정확히 100개의 인덱스(0~99) 순차 할당 및 무결성 유지 |
| `TC-PKG-001` | 패키징 & 타입 마커 | `__all__` 선언 무결성 및 PEP 561 마커 파일 검증 | - 최상위 진입점 `quiver` 모듈 임포트<br>- 배포 패키지 내 `quiver/py.typed` 파일 존재 여부 | - `quiver.__all__`에 35개 공개 유틸리티 심볼이 누락 없이 정의되어 있으며, 최상위 네임스페이스에서 직접 임포트 가능<br>- `quiver/py.typed` 파일이 존재하여 다운스트림의 `mypy --strict` 및 IDE 정적 분석기에서 인라인 타입 힌트 완전 인식 |
