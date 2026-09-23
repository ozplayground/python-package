# Subagent Orchestrator Package (`archon.subagents`)

## 1. 모듈 개요 및 책임 (Module Scope & Responsibility)

`archon.subagents`는 메인 에이전트의 지시에 따라 복수의 전문 서브에이전트(기획, 백엔드, 프론트엔드, 리뷰 등)를 비동기 병렬(`asyncio.gather`)로 오케스트레이션하고, 거버넌스 한도(최대 재귀 깊이, 순환 체인 차단, 세마포어)를 강제하는 책임을 담당합니다.

- **비동기 병렬 디스패치**: `invoke_subagents`를 통해 복수 서브에이전트를 동시 구동하여 단일 순차 대비 파이프라인 수행 시간을 획기적으로 단축합니다.
- **부분 실패 허용 (Partial Failure Tolerance)**: 병렬 실행 중 한 서브에이전트가 실패하거나 타임아웃되더라도, 다른 서브에이전트의 성공 결과는 보존하여 `List[SubagentResult]`로 취합합니다.
- **거버넌스 가드**:
  - 최대 재귀 호출 깊이 `max_depth = 3` 제한 (포크 폭탄 방지).
  - 불변 계통 목록(`caller_lineage`) 기반 순환 호출 체인(A $\rightarrow$ B $\rightarrow$ A) 감지 및 즉시 차단.
  - 세션당 동시 실행 세마포어(기본 최대 10개) 한도 적용.

---

## 2. 구현 대상 요구사항 (Implemented Requirements)

- **`REQ-SUB-001`**: 모듈러 다중 서브에이전트 비동기 동시 호출 (`FUNC-SUB-001`, `FUNC-SUB-002`)
- **`REQ-BUS-001`**: 반응형 이벤트 메시지 버스 연동 (`FUNC-CORE-002`)

---

## 3. 공개 클래스 및 인터페이스 목록 (Public Classes & Interfaces)

| 클래스/인터페이스 | 설명 | 핵심 메서드 / 속성 |
| :--- | :--- | :--- |
| `SubagentDispatcher` | 병렬 비동기 디스패처 및 거버넌스 가드 | `dispatch()`, `_validate_request()`, `concurrency_limit`, `max_depth` |
| `SubagentRunner` | 격리된 단일 서브에이전트 실행기 | `run()`, `session`, `timeout_seconds` |
| `SubagentDefinition` | 서브에이전트 정적 명세 DTO | `name`, `system_prompt`, `allowed_tools`, `required_skills`, `timeout_seconds` |
| `SubagentRequest` | 서브에이전트 호출 요청 DTO | `subagent_name`, `prompt`, `context`, `timeout_seconds` |
| `SubagentResult` | 서브에이전트 실행 결과 DTO | `subagent_name`, `is_success`, `output`, `error`, `is_timeout`, `duration_ms` |
| `invoke_subagents` | 최상위 서브에이전트 비동기 호출 함수 | `await invoke_subagents(session, requests, context)` |

---

## 4. 타 모듈과의 의존성 제약 (Dependency Rules)

- **컨텍스트 격리**: 서브에이전트는 메인 세션의 불변 명세를 참조하되, 로컬 프롬프트와 변수 공간은 `child_context`로 분리되어 부모나 형제 서브에이전트로 유출되지 않습니다.
- **이벤트 전파**: 서브에이전트의 시작, 완료, 에러 상태는 세션 내 `MessageBus`를 통해 디커플링 전파됩니다.

---

## 5. 단위 테스트 실행 가이드 및 주요 엣지 케이스 (Testing Guide)

```bash
# Subagents 모듈 관련 테스트 실행
pytest tests/test_subagents.py tests/test_subagent_runner_and_helpers.py -v
```

### 주요 검증 엣지 케이스
- **재귀 깊이 초과 차단**: 4단계 깊이 호출 시 즉시 `SubagentDepthExceededError` 발생.
- **다중 홉 순환 감지**: A $\rightarrow$ B $\rightarrow$ C $\rightarrow$ A 순환 체인 시 `SubagentCycleDetectedError` 발생.
- **부분 실패 격리**: 1개 에이전트 타임아웃 시 `is_timeout=True` 마킹 및 나머지 성공 결과 정상 보존.
- **세마포어 동시성 제어**: 100개 요청 동시 인입 시 최대 10개 한도로 순차 스케줄링.
