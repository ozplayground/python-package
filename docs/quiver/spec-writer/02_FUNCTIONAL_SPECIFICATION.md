# [quiver] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-23
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. 기능 계층 구조도 (Feature Hierarchy Tree)

```
[1Depth: quiver]
  ├── [2Depth: 컬렉션 조작 (collections)]
  │     ├── [3Depth: 청크 분할 및 지연 이터레이션] (chunk)
  │     ├── [3Depth: 다차원 리스트/이터러블 평탄화] (flatten)
  │     ├── [3Depth: 키 추출기 기준 딕셔너리 그룹화] (group_by)
  │     ├── [3Depth: 술어 함수 기준 2개 분할] (partition)
  │     ├── [3Depth: 중복 제거 및 고유 순서 유지] (uniq_by)
  │     ├── [3Depth: 슬라이딩 윈도우 시퀀스 생성] (windowed)
  │     ├── [3Depth: 중첩 딕셔너리 안전 접근 및 불변 갱신] (deep_get, deep_set)
  │     ├── [3Depth: 심층 딕셔너리 재귀 병합] (merge)
  │     └── [3Depth: 딕셔너리 키 화이트리스트/블랙리스트 필터링] (pick, omit)
  │
  ├── [2Depth: 함수 동작 및 실행 제어 (behavior)]
  │     ├── [3Depth: 좌->우 단방향 데이터 파이프라인] (pipe)
  │     ├── [3Depth: 우->좌 수학적 함수 합성] (compose)
  │     ├── [3Depth: 다인자 함수 부분 적용 커링] (curry)
  │     ├── [3Depth: 멱등적 1회 실행 보장 데코레이터] (once)
  │     ├── [3Depth: 호출 침묵 후 지연 실행] (debounce)
  │     ├── [3Depth: 지정 주기 내 최대 1회 실행 빈도 제한] (throttle)
  │     ├── [3Depth: 시간 만료 기반 스레드 세이프 캐시] (memoize with TTL)
  │     └── [3Depth: 지수 백오프 및 풀 지터 자동 재시도] (retry)
  │
  ├── [2Depth: 문자열 변환 및 보안 (strings)]
  │     ├── [3Depth: 케이스 변환 (camel, snake, kebab, pascal, title)] (case conversions)
  │     ├── [3Depth: URL 친화적 정규 슬러그 생성] (slugify)
  │     ├── [3Depth: 단어 경계 보존 및 말줄임표 처리] (truncate)
  │     └── [3Depth: 개인정보 및 금융 민감정보 마스킹] (mask_sensitive)
  │
  ├── [2Depth: 스코프 확장 및 널 안전성 (scope)]
  │     ├── [3Depth: 객체 컨텍스트 변환 및 매핑 체이닝] (let)
  │     ├── [3Depth: 불변 객체 유지 및 부수효과 탭 로깅] (also / tap)
  │     ├── [3Depth: 술어 충족 시 값 보존, 불일치 시 None 필터링] (take_if)
  │     ├── [3Depth: 술어 충족 시 None 배제, 불일치 시 값 보존] (take_unless)
  │     └── [3Depth: 첫 번째 유효(Non-None) 값 안전 추출] (coalesce)
  │
  └── [2Depth: 타이밍 및 호출율 제어 (timing)]
        ├── [3Depth: 나노초 정밀도 랩/구간 기록 스톱워치] (Stopwatch)
        ├── [3Depth: 컨텍스트 매니저 및 데코레이터 겸용 지연시간 측정] (measure_time)
        └── [3Depth: 토큰 버킷 알고리즘 기반 스레드 안전 호출율 제한기] (RateLimiter)
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

모든 단위 기능은 모듈러 상세기능정의서([`fsd/QUIVER_UTILITIES_SPECIFICATION.md`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md))에 7대 상세 명세가 완비되어 있습니다.

| 기능 ID | 1Depth (도메인) | 2Depth (모듈) | 3Depth (단위기능명) | 우선순위 | 대응 요구사항 ID | 상세 명세 문서 링크 |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| `FUNC-COLL-001` | 컬렉션 | `collections` | 불변 컬렉션 고급 다형 연산 (chunk, flatten, group_by, partition, uniq_by, windowed, deep_get/set, merge, pick/omit) | **Must** | `REQ-COLL-001` | [`fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-coll-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-coll-001) |
| `FUNC-BEHV-001` | 함수 동작 | `behavior` | 함수 제어 및 합성 데코레이터 (pipe, compose, curry, once, debounce, throttle, memoize with TTL, retry) | **Must** | `REQ-BEHV-001` | [`fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-behv-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-behv-001) |
| `FUNC-STR-001` | 문자열 | `strings` | 문자열 케이스 변환 및 보안 트랜스포머 (case conversions, slugify, truncate, mask_sensitive) | **Must** | `REQ-STR-001` | [`fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-str-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-str-001) |
| `FUNC-SCP-001` | 스코프 | `scope` | 스코프 확장 및 널 안전 체이닝 (let, also/tap, take_if, take_unless, coalesce) | **Must** | `REQ-SCP-001` | [`fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-scp-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-scp-001) |
| `FUNC-TIME-001` | 타이밍 | `timing` | 고정밀 시간 측정 및 토큰 버킷 호출율 제어 (Stopwatch, measure_time, RateLimiter) | **Must** | `REQ-TIME-001` | [`fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-time-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-time-001) |

---

## 3. 도메인별 분할 명세서 맵 (Modular FSD Map)

- [모던 전천후 유틸리티 툴킷 상세기능정의서 (QUIVER_UTILITIES_SPECIFICATION.md)](./fsd/QUIVER_UTILITIES_SPECIFICATION.md)
  - `FUNC-COLL-001`: 컬렉션 고급 다형 연산 모듈 (`quiver.collections`)
    - `chunk(iterable, size, step=None)`: 리스트/이터러블 균등 분할
    - `flatten(iterable, depth=None)`: 임의 깊이 평탄화
    - `group_by(iterable, key_fn)`: 키 기준 그룹화 딕셔너리 생성
    - `partition(predicate, iterable)`: 참/거짓 튜플 분할
    - `uniq_by(iterable, key_fn=None)`: 순서 보존 고유 원소 추출
    - `windowed(iterable, size, step=1, fill_value=...)`: 슬라이딩 윈도우 생성
    - `deep_get(mapping, path, default=None)`: 중첩 딕셔너리 안전 경로 탐색
    - `deep_set(mapping, path, value)`: 불변 복제 기반 심층 경로 갱신
    - `merge(*mappings, deep=True)`: 다중 딕셔너리 심층 재귀 병합
    - `pick(mapping, *keys)` / `omit(mapping, *keys)`: 키 선택 및 제외
  - `FUNC-BEHV-001`: 함수 동작 제어 및 합성 모듈 (`quiver.behavior`)
    - `pipe(value, *fns)`: 좌에서 우로 이어지는 단방향 데이터 전달
    - `compose(*fns)`: 우에서 좌로 실행되는 함수 합성
    - `curry(fn, arity=None)`: 인자 부분 적용 및 커링 함수
    - `once(fn)`: 다중 스레드 환경 멱등 1회 호출 보장 데코레이터
    - `debounce(wait_seconds)`: 후행/선행 디바운스 타이머 데코레이터
    - `throttle(interval_seconds)`: 주기당 최대 1회 실행 쓰로틀링 데코레이터
    - `memoize(ttl_seconds=None, maxsize=128)`: TTL 및 LRU 기반 스레드 세이프 메모이제이션
    - `retry(max_attempts=3, backoff=..., jitter=True, exceptions=(Exception,))`: 지수 백오프 스마트 재시도
  - `FUNC-STR-001`: 문자열 변환 및 보안 모듈 (`quiver.strings`)
    - 케이스 변환군: `to_camel_case`, `to_snake_case`, `to_kebab_case`, `to_pascal_case`, `to_title_case`
    - `slugify(text, separator='-', allow_unicode=False)`: URL 정규화 슬러그 생성
    - `truncate(text, length, suffix='...', preserve_words=True)`: 단어 경계 보존 말줄임
    - `mask_sensitive(text, mask_char='*', keep_prefix=..., keep_suffix=..., pattern_type=None)`: 개인정보 및 금융 마스킹
  - `FUNC-SCP-001`: 스코프 확장 및 널 안전 모듈 (`quiver.scope`)
    - `let(target, block)`: 객체 변환 함수 적용 후 결과 반환
    - `also(target, block)` / `tap(target, block)`: 부수효과 수행 후 원본 객체 반환
    - `take_if(target, predicate)`: 조건 만족 시 자기 자신, 불만족 시 `None`
    - `take_unless(target, predicate)`: 조건 만족 시 `None`, 불만족 시 자기 자신
    - `coalesce(*values)`: 가변 인자 중 첫 번째 `None`이 아닌 값 반환
  - `FUNC-TIME-001`: 고정밀 시간 측정 및 호출 제어 모듈 (`quiver.timing`)
    - `Stopwatch`: 정밀 모노토닉 타이머, 시작/정지/경과/랩(Lap) 타임 기록
    - `measure_time(callback=None, unit='ms')`: 데코레이터 및 `with` 컨텍스트 매니저 겸용 소요시간 측정
    - `RateLimiter(rate, per_seconds=1.0, burst=None)`: 토큰 버킷 기반 멀티스레드 안전 호출 속도 제한기
