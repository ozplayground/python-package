# [quiver] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-23
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.1
- **상태**: Approved

---

## 1. 기능 계층 구조도 (Feature Hierarchy Tree)

```
[1Depth: quiver]
  ├── [2Depth: 컬렉션 조작 (collections)]
  │     ├── [3Depth: 청크 분할 및 지연 이터레이션] (chunk)
  │     ├── [3Depth: 다차원 리스트/이터러블 평탄화] (flatten)
  │     ├── [3Depth: 키 추출 함수 기준 딕셔너리 그룹화] (group_by)
  │     ├── [3Depth: 조건 참/거짓 기준 2개 분할] (partition)
  │     ├── [3Depth: 원래 순서를 보존하는 중복 제거] (uniq_by)
  │     ├── [3Depth: 슬라이딩 윈도우 시퀀스 생성] (windowed)
  │     ├── [3Depth: 중첩 딕셔너리 안전 접근 및 불변 갱신] (deep_get, deep_set)
  │     ├── [3Depth: 중첩 딕셔너리 재귀 병합] (merge)
  │     └── [3Depth: 딕셔너리 키 화이트리스트/블랙리스트 필터링] (pick, omit)
  │
  ├── [2Depth: 함수 제어 및 합성 (behavior)]
  │     ├── [3Depth: 좌에서 우로 값 순차 전달 파이프라인] (pipe)
  │     ├── [3Depth: 우에서 좌로 함수 합성] (compose)
  │     ├── [3Depth: 다인자 함수 부분 적용 커링] (curry)
  │     ├── [3Depth: 멀티스레드 환경 1회 실행 보장 데코레이터] (once)
  │     ├── [3Depth: 마지막 호출 후 대기 지연 실행] (debounce)
  │     ├── [3Depth: 주기당 최대 1회 실행 제한] (throttle)
  │     ├── [3Depth: TTL 기반 스레드 안전 캐시] (memoize with TTL)
  │     └── [3Depth: 지수 백오프 및 풀 지터 자동 재시도] (retry)
  │
  ├── [2Depth: 문자열 변환 및 보안 (strings)]
  │     ├── [3Depth: 케이스 변환 (camel, snake, kebab, pascal, title)] (case conversions)
  │     ├── [3Depth: URL 슬러그 생성 및 유니코드 정규화] (slugify)
  │     ├── [3Depth: 단어 경계 보존 말줄임표 처리] (truncate)
  │     └── [3Depth: 개인정보 및 결제정보 패턴 마스킹] (mask_sensitive)
  │
  ├── [2Depth: 스코프 확장 및 None 안전성 (scope)]
  │     ├── [3Depth: 객체 컨텍스트 변환 및 매핑] (let)
  │     ├── [3Depth: 객체 불변 반환 및 사이드이펙트 로깅] (also / tap)
  │     ├── [3Depth: 조건 부합 시 값 유지, 불일치 시 None] (take_if)
  │     ├── [3Depth: 조건 부합 시 None, 불일치 시 값 유지] (take_unless)
  │     └── [3Depth: 첫 번째 유효(Non-None) 값 안전 추출] (coalesce)
  │
  └── [2Depth: 시간 계측 및 속도 제어 (timing)]
        ├── [3Depth: 나노초 정밀도 구간/랩 계측] (Stopwatch)
        ├── [3Depth: 컨텍스트 매니저 및 데코레이터 소요시간 측정] (measure_time)
        └── [3Depth: 토큰 버킷 기반 스레드 안전 속도 제한기] (RateLimiter)
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

각 기능의 상세 동작, 타입 시그니처, 엣지 케이스 및 데이터 명세는 [모듈러 상세기능정의서 (`fsd/QUIVER_UTILITIES_SPECIFICATION.md`)](./fsd/QUIVER_UTILITIES_SPECIFICATION.md)에 기술되어 있습니다.

| 기능 ID | 도메인 모듈 | 단위기능 그룹 | 핵심 함수 목록 | 우선순위 | 대응 요구사항 ID | 상세 링크 |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `FUNC-COLL-001` | `collections` | 불변 컬렉션 조작 | `chunk`, `flatten`, `group_by`, `partition`, `uniq_by`, `windowed`, `deep_get`, `deep_set`, `merge`, `pick`, `omit` | **Must** | `REQ-COLL-001` | [`QUIVER_UTILITIES_SPECIFICATION.md#func-coll-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-coll-001) |
| `FUNC-BEHV-001` | `behavior` | 함수 제어 및 합성 | `pipe`, `compose`, `curry`, `once`, `debounce`, `throttle`, `memoize`, `retry` | **Must** | `REQ-BEHV-001` | [`QUIVER_UTILITIES_SPECIFICATION.md#func-behv-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-behv-001) |
| `FUNC-STR-001` | `strings` | 문자열 변환 및 보안 | `to_camel_case`, `to_snake_case`, `to_kebab_case`, `to_pascal_case`, `to_title_case`, `slugify`, `truncate`, `mask_sensitive` | **Must** | `REQ-STR-001` | [`QUIVER_UTILITIES_SPECIFICATION.md#func-str-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-str-001) |
| `FUNC-SCP-001` | `scope` | 스코프 확장 및 None 안전성 | `let`, `also` (`tap`), `take_if`, `take_unless`, `coalesce` | **Must** | `REQ-SCP-001` | [`QUIVER_UTILITIES_SPECIFICATION.md#func-scp-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-scp-001) |
| `FUNC-TIME-001` | `timing` | 시간 계측 및 속도 제한 | `Stopwatch`, `measure_time`, `RateLimiter` | **Must** | `REQ-TIME-001` | [`QUIVER_UTILITIES_SPECIFICATION.md#func-time-001`](./fsd/QUIVER_UTILITIES_SPECIFICATION.md#func-time-001) |

---

## 3. 모듈러 FSD 연계 맵 (Modular FSD Map)

- [quiver 유틸리티 상세기능정의서 (QUIVER_UTILITIES_SPECIFICATION.md)](./fsd/QUIVER_UTILITIES_SPECIFICATION.md)
  - **`quiver.collections` (`FUNC-COLL-001`)**:
    - 대량 데이터 처리를 위한 제너레이터 기반 청크 및 슬라이딩 윈도우.
    - Copy-on-Write 기반의 원본 보존 중첩 딕셔너리 안전 갱신 (`deep_set`, `merge`).
    - 문자열과 바이트를 원자적 원소로 취급하여 불필요한 분해를 방지하는 평탄화 (`flatten`).
  - **`quiver.behavior` (`FUNC-BEHV-001`)**:
    - `threading.Lock`을 활용한 멱등성 보장 1회 실행 래퍼 (`once`).
    - API 재시도 폭풍(Thundering Herd)을 방지하는 Full Jitter 지수 백오프 (`retry`).
    - 시간 기반 만료와 메모리 상한을 관리하는 스레드 세이프 캐시 (`memoize`).
  - **`quiver.strings` (`FUNC-STR-001`)**:
    - 대소문자 전환과 구분자를 정규식으로 정확히 분리하는 케이스 변환기.
    - 단어 중간을 임의로 자르지 않고 자연스러운 문맥을 유지하는 말줄임 (`truncate`).
    - 정규식 역추적(ReDoS) 위험이 없는 주민번호, 이메일, 전화번호, 카드번호 마스킹 (`mask_sensitive`).
  - **`quiver.scope` (`FUNC-SCP-001`)**:
    - 임시 변수 스코프 오염을 방지하는 `let` 및 체이닝 중간 로깅용 `also`/`tap`.
    - `None` 값 검증과 폴백 처리를 한 줄로 정리하는 `take_if`, `coalesce`.
  - **`quiver.timing` (`FUNC-TIME-001`)**:
    - 나노초 단위 OS 모노토닉 타이머 기반의 구간 기록 `Stopwatch`.
    - 분산 트래픽 방어와 초당 요청량 제어를 위한 멀티스레드 토큰 버킷 `RateLimiter`.
