# [archon] 서브에이전트 오케스트레이터 상세기능정의서 (Subagent Orchestrator Modular FSD)

- **도메인**: 분산 서브에이전트 비동기 병렬 오케스트레이션 및 재귀/순환 방지 제어
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 단위 기능 상세 명세 (단위기능별 7대 상세 명세 완비)

---

### [FUNC-SUB-001] 모듈러 다중 서브에이전트 비동기 동시 호출 (`invoke_subagents`)

#### 0. 대응 요구사항 및 인수 판정 기준 바인딩 (Requirements & Acceptance Criteria Binding)
- **대응 요구사항 ID**: `REQ-SUB-001` (모듈러 다중 서브에이전트 비동기 동시 호출)
- **정상 판정 기준 (Happy Path)**:
  - 메인 에이전트가 `invoke_subagents(subagents=[...], tasks=[...])`를 호출하면 `asyncio.gather(..., return_exceptions=True)` 기반으로 복수 서브에이전트를 비동기 병렬 실행해야 한다.
  - 모든 서브에이전트 완료 시 각 에이전트의 출력, 소요시간(ms), 성공 여부를 취합한 `List[SubagentResult]`를 반환해야 한다.
  - 서브에이전트는 지정된 동시성 세마포어(기본 최대 10개) 한도 내에서 스케줄링되어야 한다.
- **예외/실패 판정 기준 (Edge/Exception Path)**:
  - 특정 서브에이전트가 `subagent_timeout`(기본 120초)을 초과한 경우 해당 서브에이전트만 `is_timeout=True`로 마킹되고 다른 병렬 에이전트의 성공 결과는 정상 보존되어야 한다 (`Partial Failure Tolerance`).
  - 미등록 서브에이전트 호출 시 즉시 `SubagentNotFoundError` (`ERR_SUB_NOT_FOUND`)를 반환해야 한다.
- **단위 테스트 검증 조건 (TDD Target)**:
  - 5개 서브에이전트 병렬 호출 1,000회 스트레스 테스트 시 데드락 없는 완료율 $\ge 99.5\%$.
  - 1개 서브에이전트 강제 실패/타임아웃 시 나머지 4개 성공 결과 보존률 $100\%$.

#### 1. 기본 정보
- **기능명**: 모듈러 다중 서브에이전트 비동기 동시 호출 (`invoke_subagents`)
- **기능 ID**: `FUNC-SUB-001`
- **대응 요구사항 ID**: `REQ-SUB-001`
- **대상 모듈 코드**: `MOD-ORCH-001`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 메인 에이전트, 파이프라인 오케스트레이터

#### 2. 사전 조건 (Pre-conditions)
1. 세션 내에 호출 대상 서브에이전트(예: `backend-tdd-engineer`, `frontend-tdd-engineer`)가 등록되어 있는 상태.
2. `FUNC-SUB-002`의 재귀 깊이 및 순환 호출 검사를 사전 통과한 상태.

#### 3. 사용자 인터랙션 및 시스템 동작 흐름과 플로우차트 (Step-by-Step Flow & Flowchart)

1. 메인 에이전트가 `await session.invoke_subagents([req1, req2, ...])`를 호출합니다.
2. 오케스트레이터는 세마포어(`asyncio.Semaphore(10)`)를 획득한 후 `asyncio.gather(*tasks, return_exceptions=True)`로 각 서브에이전트 코루틴을 스폰합니다.
3. 각 서브에이전트는 독립된 컨텍스트에서 LLM 질의, 도구 실행, 스킬 주입을 수행합니다.
4. 개별 서브에이전트에 설정된 타임아웃(`timeout_seconds`, 기본 120초)을 초과하면 해당 태스크에 `CancelledError`를 주입하고 `is_timeout=True`로 패키징합니다.
5. 모든 서브에이전트의 실행이 완료되면 예외 발생 여부를 분석하여 `List[SubagentResult]`로 취합 반환합니다.

```mermaid
flowchart TD
    A[invoke_subagents 호출] --> B[동시성 세마포어 획득: 최대 10개]
    B --> C[asyncio.gather 기반 비동기 병렬 스폰]
    C --> D1[서브에이전트 1 실행 (e.g. Backend TDD)]
    C --> D2[서브에이전트 2 실행 (e.g. Frontend TDD)]
    D1 --> E1{타임아웃 120s 내 완료?}
    D2 --> E2{타임아웃 120s 내 완료?}
    E1 -- 성공 --> F1[SubagentResult: is_success=True]
    E1 -- 초과 --> F2[SubagentResult: is_timeout=True]
    E2 -- 성공 --> F3[SubagentResult: is_success=True]
    E2 -- 실패 --> F4[SubagentResult: error_detail 바인딩]
    F1 --> G[return_exceptions=True 결과 집계]
    F2 --> G
    F3 --> G
    F4 --> G
    G --> H[호출자에게 List[SubagentResult] 반환]
```

#### 4. 데이터 항목 명세 (Data Elements - 8대 표준 컬럼)

| 항목명 | 입출력 구분 | UI/호출 타입 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출/수정 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `subagent_name` | 요청 인자 | String | 필수 | String / 등록된 서브에이전트 식별자 | - | 영문 소문자 및 하이픈 | 항상 필수 |
| `task_prompt` | 요청 인자 | String | 필수 | String / 1자 이상 50,000자 이하 | - | 공백 제외 1자 이상 | 항상 필수 |
| `context_data` | 요청 인자 | Dict | 선택 | `Dict[str, Any]` | `{}` | JSON 직렬화 가능 딕셔너리 | 부모 데이터 전달 시 |
| `timeout_seconds` | 요청 인자 | Float | 선택 | Float / 1.0 ~ 600.0 (초) | `120.0` | $1.0 \le \text{timeout} \le 600.0$ | 개별 요청 타임아웃 지정 시 |
| `is_success` | 반환 속성 | Boolean | 필수 | Boolean | `False` | 서브에이전트 정상 완료 여부 | 항상 반환 |
| `result_data` | 반환 속성 | Any | 선택 | String 또는 Dict | `None` | 서브에이전트 최종 출력 산출물 | 성공 시 반환 |
| `error_detail` | 반환 속성 | Optional | 선택 | `Optional[SubagentErrorDetail]` | `None` | 실패 시 예외 메시지 및 에러 코드 | 실패 시 반환 |
| `duration_ms` | 반환 속성 | Float | 필수 | Float ($t \ge 0.0$) | `0.0` | 서브에이전트 실행 소요 시간 | 항상 반환 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-SUB-001-1**: 복수 서브에이전트는 완전히 비동기 병렬로 동시 실행되어야 하며, 전체 오케스트레이션 소요 시간은 $\max(T_1, T_2, \dots) + \text{오버헤드}$에 수렴해야 합니다.
- **BR-SUB-001-2**: 개별 서브에이전트의 크래시나 타임아웃이 다른 병렬 서브에이전트의 실행을 중단시키지 않아야 합니다 (`Fault Isolation`).
- **BR-SUB-001-3**: 모든 서브에이전트 호출은 메인 에이전트의 세션 컨텍스트를 상속받되, 로컬 변수나 인메모리 상태는 독립 컨텍스트로 격리되어야 합니다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 시스템 처리 방식 | 사용자 안내 메시지 / 예외 |
| :--- | :--- | :--- |
| 한 서브에이전트가 120초 타임아웃에 도달한 경우 | 해당 서브에이전트 코루틴만 취소하고 `is_timeout=True`, `ERR_SUB_TIMEOUT` 기록 | `SubagentResult(is_success=False, error_detail=SubagentErrorDetail(code="ERR_SUB_TIMEOUT"))` |
| 미등록 서브에이전트 호출 시도 시 | 병렬 디스패치 전 즉시 유효성 검사에서 차단 | `SubagentNotFoundError: Subagent 'invalid-agent' is not registered in session` |
| 서브에이전트 내부에서 처리되지 않은 Python 예외 발생 시 | 예외 스택 트레이스를 `SubagentErrorDetail`에 보존하고 `is_success=False` 처리 | `SubagentResult(is_success=False, error_detail=SubagentErrorDetail(code="ERR_SUB_EXECUTION_FAILED"))` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 원인 | 예외 클래스 | 대응 가이드 |
| :--- | :--- | :--- | :--- |
| `ERR_SUB_TIMEOUT` | 서브에이전트 개별 타임아웃 초과 | `SubagentTimeoutError` | timeout_seconds 설정 상향 또는 프롬프트 분할 |
| `ERR_SUB_NOT_FOUND` | 미등록 서브에이전트 호출 | `SubagentNotFoundError` | 하네스 내 subagents 정의 확인 |
| `ERR_SUB_EXECUTION_FAILED` | 서브에이전트 런타임 예외 발생 | `SubagentExecutionError` | 에러 스택 트레이스 및 입력 파라미터 점검 |

---

### [FUNC-SUB-002] 서브에이전트 재귀 깊이 제어 및 순환 방지 (Depth Limiter & Cycle Detector)

#### 0. 대응 요구사항 및 인수 판정 기준 바인딩 (Requirements & Acceptance Criteria Binding)
- **대응 요구사항 ID**: `REQ-SUB-001` (모듈러 다중 서브에이전트 비동기 동시 호출)
- **정상 판정 기준 (Happy Path)**:
  - 호출 계통(`caller_lineage`)의 깊이가 `max_subagent_depth`(기본 3) 이하이고 순환 종속성이 없는 경우 정상 통과(`True`)를 판정해야 한다.
- **예외/실패 판정 기준 (Edge/Exception Path)**:
  - 호출 체인 깊이가 3단계를 초과할 경우 `SubagentDepthExceededError` (`ERR_SUB_DEPTH_EXCEEDED`)를 발생시키며 즉시 실행을 거부해야 한다.
  - 부모 계통 리스트에 대상 서브에이전트 식별자가 이미 존재하는 순환 호출(`A -> B -> A`) 감지 시 `SubagentCycleDetectedError` (`ERR_SUB_CYCLE_DETECTED`)를 발생시켜야 한다.
- **단위 테스트 검증 조건 (TDD Target)**:
  - 4단계 깊이 호출 진입 시 차단율 $100\%$.
  - 순환 호출 체인 10종 모의 주입 시 탐지 차단율 $100\%$.

#### 1. 기본 정보
- **기능명**: 서브에이전트 재귀 깊이 제어 (`max_depth=3`) 및 순환 방지
- **기능 ID**: `FUNC-SUB-002`
- **대응 요구사항 ID**: `REQ-SUB-001`
- **대상 모듈 코드**: `MOD-ORCH-002`
- **우선순위**: Must Have
- **관련 액터 (Actor)**: 오케스트레이션 가드, 서브에이전트 디스패처

#### 2. 사전 조건 (Pre-conditions)
1. 서브에이전트 호출 요청 시 호출자의 부모 계통(`caller_lineage: List[str]`)이 전달된 상태.

#### 3. 사용자 인터랙션 및 시스템 동작 흐름과 플로우차트 (Step-by-Step Flow & Flowchart)

1. 서브에이전트 디스패처가 `OrchestrationGuard.validate_call(target_agent, caller_lineage)`를 호출합니다.
2. **깊이 검증**: `len(caller_lineage)`가 `max_depth`(3) 이상인지 검사합니다.
   - $depth \ge 3$이면 즉시 `SubagentDepthExceededError` 발생.
3. **순환 검증**: `target_agent in caller_lineage` 조건을 검사합니다.
   - 이미 부모 계통에 존재하는 에이전트명이면 즉시 `SubagentCycleDetectedError` 발생.
4. 모든 검증을 통과하면 새로운 계통 리스트(`caller_lineage + [target_agent]`)를 생성하여 실행 컨텍스트에 바인딩합니다.

```mermaid
flowchart TD
    A[validate_call(target, lineage) 호출] --> B{현재 깊이 depth >= max_depth(3)?}
    B -- 참 (깊이 한도 초과) --> C[SubagentDepthExceededError 발생 및 차단]
    B -- 거짓 (통과) --> D{target in caller_lineage (순환 참조)?}
    D -- 참 (순환 발견) --> E[SubagentCycleDetectedError 발생 및 차단]
    D -- 거짓 (통과) --> F[새 lineage 생성: caller_lineage + [target]]
    F --> G[호출 승인 및 서브에이전트 디스패치 진행]
```

#### 4. 데이터 항목 명세 (Data Elements - 8대 표준 컬럼)

| 항목명 | 입출력 구분 | UI/호출 타입 | 필수 여부 | 데이터 타입 / 제약 | 기본값 | 유효성 검증 규칙 (Validation) | 노출/수정 조건 |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| `target_agent` | 입력 인자 | String | 필수 | String / 서브에이전트 식별자 | - | 영문 소문자 및 하이픈 | 항상 필수 |
| `caller_lineage`| 입력 인자 | List | 필수 | `List[str]` / 부모 호출 스택 | `[]` | 호출 계통 순서 보존 리스트 | 항상 필수 |
| `max_depth` | 설정 인자 | Integer | 필수 | Integer / 1 ~ 5 | `3` | $1 \le \text{max\_depth} \le 5$ | 시스템 설정 |
| `current_depth` | 계산 속성 | Integer | 필수 | Integer ($n \ge 0$) | `0` | `len(caller_lineage)` | 항상 반환 |
| `is_valid` | 반환 속성 | Boolean | 필수 | Boolean | `True` | 가드 검증 통과 시 True | 항상 반환 |
| `new_lineage` | 반환 속성 | List | 필수 | `List[str]` | - | 대상이 추가된 신규 스택 | 통과 시 반환 |
| `rejection_reason`| 상태 속성 | Optional | 선택 | String | `None` | 거부 사유 메시지 | 실패 시 반환 |
| `cycle_path` | 상태 속성 | Optional | 선택 | String | `None` | 감지된 순환 경로 (e.g. A->B->A) | 순환 감지 시 |

#### 5. 비즈니스 규칙 (Business Rules)
- **BR-SUB-002-1**: 최대 호출 깊이는 기본 3단계(`Root -> Subagent -> Nested -> Leaf`)를 엄격히 강제하며, 포크 폭탄(Fork Bomb)으로 인한 무제한 자식 생성을 방지합니다.
- **BR-SUB-002-2**: 순환 호출 탐지는 대소문자를 구분하지 않고 정규화된 에이전트 식별자를 기준으로 판정합니다.
- **BR-SUB-002-3**: 호출 계통(`caller_lineage`)은 불변 튜플 또는 복사본으로 전달되어 하위 에이전트가 임의로 조작할 수 없어야 합니다.

#### 6. 예외 처리 및 엣지 케이스 (Edge Cases & Exception Handling)

| 발생 상황 (Edge Case Scenario) | 시스템 처리 방식 | 사용자 안내 메시지 / 예외 |
| :--- | :--- | :--- |
| 3단계 깊이의 Leaf 에이전트가 서브에이전트 호출 시 | 자식 태스크 생성을 즉시 차단하고 한도 초과 에러 반환 | `SubagentDepthExceededError: Maximum subagent depth of 3 exceeded (current depth: 3)` |
| 자기 자신을 직접 호출(A -> A)하는 경우 | 순환 감지 즉시 실행 거부 | `SubagentCycleDetectedError: Direct self-invocation detected for agent 'agent_a'` |
| 3자 간 순환 호출(A -> B -> C -> A) 감지 시 | 전체 순환 경로를 명시하여 빠른 디버깅 지원 | `SubagentCycleDetectedError: Cycle detected: main -> agent_a -> agent_b -> agent_c -> agent_a` |

#### 7. 비즈니스 에러 코드 매핑

| 비즈니스 에러 코드 | 발생 원인 | 예외 클래스 | 대응 가이드 |
| :--- | :--- | :--- | :--- |
| `ERR_SUB_DEPTH_EXCEEDED` | 재귀 깊이 상한선 초과 | `SubagentDepthExceededError` | 작업 계층 단순화 또는 max_depth 설정 조정 |
| `ERR_SUB_CYCLE_DETECTED` | 부모 체인 내 순환 종속성 발생 | `SubagentCycleDetectedError` | 서브에이전트 간 호출 흐름 단방향 재구성 |
