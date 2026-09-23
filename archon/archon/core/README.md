# Core Runtime Package (`archon.core`)

## 1. 모듈 개요 및 책임 (Module Scope & Responsibility)

`archon.core`는 에이전트 실행의 심장부로서, 세션 라이프사이클 관리, 불변 실행 컨텍스트 유지, 메인 턴 추론 및 툴 실행 루프, 그리고 반응형 인메모리 이벤트 버스를 전담합니다.

- **세션 격리**: 모든 `AgentSession`은 고유 세션 ID를 소유하며, 도구 레지스트리와 스킬 레지스트리를 독립 복제하여 세션 간 프롬프트나 상태의 교차 오염을 100% 방지합니다.
- **불변 컨텍스트 보존**: `ExecutionContext`는 계층형 호출 깊이(`depth`)와 조상 에이전트 목록(`caller_lineage`)을 불변 튜플로 기록하여 포크 폭탄과 순환 호출을 차단하는 근거를 제공합니다.
- **반응형 이벤트 버스**: 인메모리 FIFO 비동기 메시지 큐와 이벤트 발행/구독(Pub/Sub) 채널을 지원하여 에이전트 간 비동기 협업을 돕습니다.

---

## 2. 구현 대상 요구사항 (Implemented Requirements)

- **`REQ-SESS-001`**: 세션 단위 하네스 동적 바인딩 및 런타임 컴파일 (`FUNC-SESS-001`, `FUNC-CORE-001`)
- **`REQ-BUS-001`**: 반응형 이벤트 메시지 버스 (`FUNC-CORE-002`)
- **`REQ-VIS-001`**: 에이전트 실행 궤적 트레이싱 (`FUNC-CORE-001`)

---

## 3. 공개 클래스 및 인터페이스 목록 (Public Classes & Interfaces)

| 클래스/인터페이스 | 설명 | 핵심 메서드 / 속성 |
| :--- | :--- | :--- |
| `AgentSession` | 에이전트 세션 수명주기 및 턴 실행기 | `run()`, `async_run()`, `stream()`, `invoke_subagents()`, `close()`, `compile_system_prompt()` |
| `ExecutionContext` | 불변 실행 프레임 및 계통 스냅샷 DTO | `session_id`, `agent_name`, `depth`, `caller_lineage`, `variables`, `create_child()` |
| `StepResult` | 단일 턴 실행 결과 모델 | `text`, `tool_calls`, `is_complete`, `metadata` |
| `MessageBus` | 반응형 P2P 및 Pub/Sub 이벤트 버스 | `send_message()`, `receive_message()`, `register_recipient()`, `publish()`, `subscribe()`, `close()` |

---

## 4. 타 모듈과의 의존성 제약 (Dependency Rules)

- **하향 의존 원칙**: `core`는 `harness`, `subagents`, `tools`, `models`를 조정할 수 있으나, 상위 애플리케이션이나 외부 프레임워크 구현체에 결합되지 않습니다.
- **순환 참조 차단**: 순환 의존 방지를 위해 `HarnessManifest` 타입 힌트는 `TYPE_CHECKING`을 통해 지연 참조하며 `from __future__ import annotations`를 적용합니다.

---

## 5. 단위 테스트 실행 가이드 및 주요 엣지 케이스 (Testing Guide)

```bash
# Core 모듈 관련 테스트 실행
pytest tests/test_session.py tests/test_message_bus.py -v
```

### 주요 검증 엣지 케이스
- **세션 타임아웃 강제 차단**: `session_timeout` 초과 시 `SessionTimeoutError` 발생 및 코루틴 취소.
- **종료된 세션 호출 방어**: `session.close()` 후 작업 요청 시 `SessionClosedError` 발생.
- **미등록 수신자 메시징 거부**: 등록되지 않은 에이전트 ID로 메시지 전송 시 `InvalidRecipientError` 발생.
- **1,000건 동시 P2P 메시징**: 인메모리 큐를 통한 1,000건 동시 전송 시 0유실 및 FIFO 순서 보장.
