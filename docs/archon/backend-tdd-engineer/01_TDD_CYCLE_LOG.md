# [archon] 백엔드 TDD 사이클 실행 기록서 (Backend TDD Log)

- **작성일자**: 2026-09-23
- **작성자**: 백엔드 TDD 엔지니어 (`backend-tdd-engineer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. TDD 개발 대상 단위 기능 및 대상 모듈

- **대응 기능 ID**:
  - `FUNC-HARN-001`, `FUNC-HARN-002` (다중 소스 하네스 프로바이더, 파서 및 ZipSlip 방어)
  - `FUNC-SESS-001`, `FUNC-CORE-001`, `FUNC-CORE-002` (세션 동적 바인딩, 라이프사이클 및 반응형 메시지 버스)
  - `FUNC-SUB-001`, `FUNC-SUB-002` (비동기 동시 서브에이전트 오케스트레이션, 재귀 깊이 및 순환 차단)
  - `FUNC-TOOL-001`, `FUNC-TOOL-002` (보안 Bash 샌드박스, 프로세스 그룹 분리, 1MB 절삭, `@tool`)
  - `FUNC-SKIL-001`, `FUNC-SKIL-002` (스킬 카탈로그, 정적 린터 및 스킬 독립성 Rule 5 강제)
  - `FUNC-MOD-001`, `FUNC-MOD-002` (멀티 LLM 어댑터, 스트리밍 및 Pydantic v2 구조화 출력 파서)
- **대상 파일**:
  - `archon/core/session.py`, `archon/core/bus.py`, `archon/core/context.py`, `archon/core/step.py`
  - `archon/harness/provider.py`, `archon/harness/fs_provider.py`, `archon/harness/memory_provider.py`, `archon/harness/db_provider.py`, `archon/harness/parser.py`, `archon/harness/manifest.py`
  - `archon/subagents/dispatcher.py`, `archon/subagents/runner.py`, `archon/subagents/definition.py`, `archon/subagents/bus.py`
  - `archon/tools/bash.py`, `archon/tools/base.py`, `archon/tools/registry.py`, `archon/tools/decorator.py`, `archon/tools/result.py`
  - `archon/skills/definition.py`, `archon/skills/registry.py`, `archon/skills/loader.py`, `archon/skills/linter.py`
  - `archon/models/base.py`, `archon/models/mock.py`, `archon/models/openai_adapter.py`, `archon/models/litellm_adapter.py`, `archon/models/structured.py`
  - `archon/factory.py`, `archon/exceptions.py`
- **테스트 파일**:
  - `tests/test_harness.py`, `tests/test_harness_factories_and_security.py`
  - `tests/test_session.py`, `tests/test_message_bus.py`
  - `tests/test_subagents.py`, `tests/test_subagent_runner_and_helpers.py`
  - `tests/test_tools.py`
  - `tests/test_skills.py`, `tests/test_skill_linter.py`
  - `tests/test_model_adapters.py`
  - `tests/test_concurrency_stress.py`, `tests/test_coverage_boost.py`, `tests/test_e2e.py`

---

## 2. Red-Green-Refactor 사이클 실행 기록

### [Cycle 1] 순환 참조 해결 및 `create_session` 세션 팩토리 TDD
#### 1. RED Phase (실패하는 테스트 작성)
- **작성된 테스트 코드**: `tests/test_e2e.py`, `tests/test_harness.py`
- **실행 결과 (실패 확인)**:
```
E   ImportError: cannot import name 'create_session' from 'archon'
E   ImportError: cannot import name 'HarnessManifest' from partially initialized module 'archon.harness.manifest' (most likely due to a circular import)
FAILED tests/test_e2e.py - 2 errors during collection
```
#### 2. GREEN Phase (최소 구현으로 통과)
- **구현 내용 요약**:
  - `from __future__ import annotations` 및 `if TYPE_CHECKING: from archon.harness.manifest import HarnessManifest` 적용으로 `core.session` ↔ `harness.manifest` ↔ `subagents.dispatcher` 간의 순환 임포트 체인 완전 해소.
  - `archon.factory.create_session` 구현: `HarnessProvider`, `HarnessManifest`, `Path`, `str`, `bytes` 입력을 자동 판별하여 컴파일된 `AgentSession` 인스턴스 반환.
- **실행 결과 (성공 확인)**:
```
tests/test_e2e.py::TestArchonEndToEnd::test_full_agent_workflow PASSED
tests/test_harness.py::TestHarnessParser::test_parse_agents_constitution_and_rules PASSED
```
#### 3. REFACTOR Phase (구조 개선 및 최적화)
- **리팩토링 내용**: 공개 패키지 진입점 `archon/__init__.py`에 `create_session`, `AgentSession`, `ExecutionContext`, `StepResult` 및 도메인 예외를 일관되게 익스포트.

---

### [Cycle 2] 반응형 메시지 버스 (`MessageBus`) 및 세션 타임아웃 TDD
#### 1. RED Phase (실패하는 테스트 작성)
- **작성된 테스트 코드**: `tests/test_message_bus.py`, `tests/test_session.py::test_session_timeout_raises_error`
```python
@pytest.mark.asyncio
async def test_p2p_send_and_receive_fifo():
    bus = MessageBus()
    bus.register_recipient("agent_a")
    bus.register_recipient("agent_b")
    await bus.send_message("agent_a", "agent_b", "msg 1")
    recv1 = await bus.receive_message("agent_b", timeout=1.0)
    assert recv1["payload"] == "msg 1"
```
- **실행 결과 (실패 확인)**:
```
E   ModuleNotFoundError: No module named 'archon.core.bus'
```
#### 2. GREEN Phase (최소 구현으로 통과)
- **구현 내용 요약**:
  - `archon/core/bus.py`에 수신자별 `asyncio.Queue` 기반 P2P 메시징 및 Pub/Sub 이벤트 버스 구현.
  - `*` 브로드캐스트 전송, `InvalidRecipientError`, `MessageBusClosedError` 방어.
  - `AgentSession.async_run`에 `session_timeout` 초과 시 `SessionTimeoutError` 발생 및 코루틴 취소 로직 연결.
- **실행 결과 (성공 확인)**:
```
tests/test_message_bus.py::TestMessageBusCore::test_p2p_send_and_receive_fifo PASSED
tests/test_message_bus.py::TestMessageBusCore::test_send_to_unregistered_recipient_raises_invalid_recipient_error PASSED
tests/test_message_bus.py::TestMessageBusCore::test_high_volume_concurrent_fifo_zero_loss PASSED
tests/test_session.py::TestAgentSession::test_session_timeout_raises_error PASSED
```
#### 3. REFACTOR Phase (구조 개선 및 최적화)
- **리팩토링 내용**: `archon.subagents.bus`에서 `archon.core.bus.MessageBus`를 re-export하여 하위 호환성 유지.

---

### [Cycle 3] 하네스 프로바이더 정적 팩토리 및 ZipSlip 보안 샌드박스 TDD
#### 1. RED Phase (실패하는 테스트 작성)
- **작성된 테스트 코드**: `tests/test_harness_factories_and_security.py`
```python
def test_factory_from_fs(tmp_path):
    provider = HarnessProvider.from_fs(tmp_path)
    assert isinstance(provider, FileSystemHarnessProvider)
```
- **실행 결과 (실패 확인)**:
```
E   AttributeError: type object 'HarnessProvider' has no attribute 'from_fs'
FAILED tests/test_harness_factories_and_security.py::TestHarnessProviderFactoriesAndEdges::test_factory_from_fs
```
#### 2. GREEN Phase (최소 구현으로 통과)
- **구현 내용 요약**:
  - `HarnessProvider`에 `from_fs`, `from_upload`, `from_db` 정적 팩토리 메서드 구현.
  - `InMemoryHarnessProvider` 내 ZipSlip 경로 탈출(`../`, `..\`, 절대경로) 차단 검증.
- **실행 결과 (성공 확인)**:
```
tests/test_harness_factories_and_security.py 9 passed in 0.05s
```
#### 3. REFACTOR Phase (구조 개선 및 최적화)
- **리팩토링 내용**: 마크다운 파일 파싱 시 프론트매터 누락 파일과 정상 파일을 결함 없이 수용하도록 `HarnessParser.parse_files` 정규화.

---

### [Cycle 4] 서브에이전트 오케스트레이터 (`SubagentRunner`, `invoke_subagents`) TDD
#### 1. RED Phase (실패하는 테스트 작성)
- **작성된 테스트 코드**: `tests/test_subagent_runner_and_helpers.py`
```python
runner = SubagentRunner(session=session)
result = await runner.run(subagent_def, request, context)
assert result.is_success is True
```
- **실행 결과 (실패 확인)**:
```
E   ImportError: cannot import name 'SubagentRunner' from 'archon.subagents'
FAILED tests/test_subagent_runner_and_helpers.py
```
#### 2. GREEN Phase (최소 구현으로 통과)
- **구현 내용 요약**:
  - `archon/subagents/runner.py`에 `SubagentRunner` 구현: 개별 서브에이전트 타임아웃 감시, 스킬 동적 주입, 모델 비동기 호출 및 `SUBAGENT_STARTED`/`COMPLETED`/`FAILED` 이벤트 발행.
  - 최상위 `invoke_subagents` 함수 구현: 세션 및 요청 시퀀스를 받아 병렬 실행 디스패치.
  - `SubagentResult`에 `is_timeout` 필드 추가.
- **실행 결과 (성공 확인)**:
```
tests/test_subagent_runner_and_helpers.py 4 passed in 0.15s
```
#### 3. REFACTOR Phase (구조 개선 및 최적화)
- **리팩토링 내용**: `SubagentDispatcher`의 단일 실행 블록을 `SubagentRunner`로 일원화 위임하여 책임 분리 및 코드 중복 제거.

---

### [Cycle 5] 스킬 독립성 정적 린터 (`SkillLinter`) TDD
#### 1. RED Phase (실패하는 테스트 작성)
- **작성된 테스트 코드**: `tests/test_skill_linter.py`
```python
linter = SkillLinter()
with pytest.raises(SkillIsolationError):
    linter.lint(content, ["tdd", "git"])
```
- **실행 결과 (실패 확인)**:
```
E   ImportError: cannot import name 'SkillLinter' from 'archon.skills'
FAILED tests/test_skill_linter.py
```
#### 2. GREEN Phase (최소 구현으로 통과)
- **구현 내용 요약**:
  - `archon/skills/linter.py`에 `SkillLinter` 구현.
  - 스킬 본문 내 라인 단위 정규식 검사를 통해 타 스킬 직접 언급, `../other/SKILL.md` 상대 경로 참조, `@skill(...)` 및 `include skill` 문법 100% 감지 및 위반 라인 번호 안내.
- **실행 결과 (성공 확인)**:
```
tests/test_skill_linter.py 4 passed in 0.05s
```
#### 3. REFACTOR Phase (구조 개선 및 최적화)
- **리팩토링 내용**: `SkillLoader.validate_isolation`에서 `SkillLinter`를 재사용하도록 연동.

---

### [Cycle 6] 멀티 LLM 어댑터 및 구조화 출력 파서 TDD
#### 1. RED Phase (실패하는 테스트 작성)
- **작성된 테스트 코드**: `tests/test_model_adapters.py`
- **실행 결과 (실패 확인)**:
```
E   ImportError: cannot import name 'LiteLLMAdapter' from 'archon.models'
FAILED tests/test_model_adapters.py
```
#### 2. GREEN Phase (최소 구현으로 통과)
- **구현 내용 요약**:
  - `archon/models/structured.py`: `StructuredOutputParser` 구현 (마크다운 백틱 코드블록 자동 언랩, Pydantic v2 `model_validate_json` 고속 검증, `ModelResponseValidationError` 상세 에러 보존).
  - `archon/models/openai_adapter.py`: HTTPX 기반 OpenAI ChatCompletions 및 SSE 스트리밍 토큰 역직렬화, 401/403 Fast-Fail, 429/5xx Full Jitter 지수 백오프 재시도.
  - `archon/models/litellm_adapter.py`: LiteLLM 멀티 프로바이더 라우터 및 오프라인 폴백.
- **실행 결과 (성공 확인)**:
```
tests/test_model_adapters.py 8 passed in 0.07s
```
#### 3. REFACTOR Phase (구조 개선 및 최적화)
- **리팩토링 내용**: 대화형 LLM 응답 텍스트 내에 포함된 JSON 블록을 정규식으로 안전하게 추출하도록 `strip_markdown_fences` 정밀화.

---

### [Cycle 7] 100개 코루틴 동시 세션/서브에이전트 부하 스트레스 검증 TDD
#### 1. RED Phase (실패하는 테스트 작성)
- **작성된 테스트 코드**: `tests/test_concurrency_stress.py`
- **실행 결과 (검증)**:
  - 100개 세션 동시 생성, 고유 툴 등록, 실행 및 격리 무결성 검증.
  - 100개 서브에이전트 동시 디스패치 및 세마포어(Max 10) 스케줄링 검증.
#### 2. GREEN Phase (최소 구현으로 통과)
- **실행 결과 (성공 확인)**:
```
tests/test_concurrency_stress.py::TestConcurrencyAndLoadStress::test_100_concurrent_sessions_zero_contamination PASSED [ 50%]
tests/test_concurrency_stress.py::TestConcurrencyAndLoadStress::test_100_concurrent_subagent_invocations PASSED [100%]
2 passed in 0.10s
```
#### 3. REFACTOR Phase (구조 개선 및 최적화)
- **리팩토링 내용**: `test_coverage_boost.py`를 통해 모든 엣지 브랜치를 보강하여 전체 라인 커버리지 91% 달성.

---

## 3. 예외 및 엣지 케이스 테스트 커버리지

| 테스트 케이스명 | 검증 시나리오 | 기대 결과 | 통과 여부 |
| :--- | :--- | :---: | :---: |
| `test_missing_agents_md_raises_error` | `AGENTS.md` 헌법 누락 하네스 로드 시 | `HarnessParseError` | PASS |
| `test_zipslip_traversal_payload_variations_blocked` | `../../etc/shadow`, `..\..\win` 등 ZipSlip 공격 주입 시 | `HarnessSecurityError` | PASS |
| `test_malformed_yaml_frontmatter_raises_parse_error` | 프론트매터 YAML 구문 불량 시 | `HarnessParseError` | PASS |
| `test_session_timeout_raises_error` | 세션 총 실행시간 100ms 초과 시 | `SessionTimeoutError` | PASS |
| `test_session_closed_raises_session_closed_error` | 종료된 세션에 재호출 시 | `SessionClosedError` | PASS |
| `test_send_to_unregistered_recipient_raises_invalid_recipient_error` | 미등록 수신자 ID로 P2P 메시지 전송 시 | `InvalidRecipientError` | PASS |
| `test_send_to_closed_message_bus_raises_error` | 닫힌 메시지 버스에 전송 시 | `MessageBusClosedError` | PASS |
| `test_subagent_not_found_raises_error` | 미등록 서브에이전트 호출 시 | `SubagentNotFoundError` | PASS |
| `test_max_depth_exceeded_raises_error` | 재귀 깊이 3 초과(depth=4) 호출 시 | `SubagentDepthExceededError` | PASS |
| `test_circular_lineage_detected_raises_error` | A $\rightarrow$ B $\rightarrow$ A 순환 체인 시 | `SubagentCycleDetectedError` | PASS |
| `test_multi_hop_cycle_detection` | A $\rightarrow$ B $\rightarrow$ C $\rightarrow$ A 순환 체인 시 | `SubagentCycleDetectedError` | PASS |
| `test_partial_failure_fault_tolerance` | 서브에이전트 1개 실패 시 | 타 에이전트 성공 결과 100% 보존 | PASS |
| `test_subagent_runner_timeout_marks_is_timeout` | 개별 서브에이전트 100ms 초과 시 | `is_timeout=True`, 실패 처리 | PASS |
| `test_blocked_dangerous_commands_blacklist` | `rm -rf /`, `sudo`, `mkfs`, 포크폭탄 등 14종 주입 시 | `ToolSecurityError` | PASS |
| `test_directory_jail_prevents_escaping_working_dir` | `cd /`, `cd ../..` 등 Jail 외부 탈출 시 | `ToolSecurityError` | PASS |
| `test_execute_timeout_kills_process_group` | 셸 5초 슬립에 0.2초 타임아웃 부여 시 | 프로세스 그룹 SIGKILL, code=124 | PASS |
| `test_large_output_buffer_truncation` | 1.2MB 콘솔 출력 발생 시 | 1MB 절삭 및 플래그 설정 | PASS |
| `test_cross_skill_name_reference_raises_skill_isolation_error` | 스킬 본문에서 타 스킬 이름 언급 시 | `SkillIsolationError` (Rule 5) | PASS |
| `test_cross_skill_relative_path_reference_raises_isolation_error` | 스킬 본문에서 `../other/SKILL.md` 참조 시 | `SkillIsolationError` (Rule 5) | PASS |
| `test_lint_detects_import_or_decorator_syntax` | `@skill(...)` 또는 `include skill` 사용 시 | `SkillIsolationError` (Rule 5) | PASS |
| `test_parse_invalid_json_raises_validation_error` | LLM이 비-JSON 반환 시 | `ModelResponseValidationError` | PASS |
| `test_parse_schema_mismatch_raises_validation_error` | 필수 필드 누락 JSON 반환 시 | `ModelResponseValidationError` | PASS |
| `test_authentication_error_fast_fails` | OpenAI HTTP 401 수신 시 | `ModelAuthenticationError` 즉시 발생 | PASS |
| `test_100_concurrent_sessions_zero_contamination` | 100개 세션 동시 실행 시 | 프롬프트/툴 레지스트리 오염 0건 | PASS |
| `test_100_concurrent_subagent_invocations` | 100개 서브에이전트 동시 디스패치 시 | 데드락 없이 100% 완료 | PASS |

---

## 4. 최종 테스트 커버리지 리포트

- **전체 라인 커버리지**: **`91%`** (목표 $\ge 85\%$ 및 PRD KPI $\ge 90\%$ 초과 달성)
- **통과 테스트 수**: **74건 전수 통과 (0건 실패)**
- **실행 명령어**: `pytest --cov=archon --cov-report=term-missing`

```
Name                                Stmts   Miss  Cover   Missing
-----------------------------------------------------------------
archon/__init__.py                      7      0   100%
archon/core/__init__.py                 5      0   100%
archon/core/bus.py                     74      9    88%
archon/core/context.py                 13      0   100%
archon/core/session.py                107      7    93%
archon/core/step.py                     8      0   100%
archon/exceptions.py                   42      0   100%
archon/factory.py                      41      7    83%
archon/harness/__init__.py              7      0   100%
archon/harness/db_provider.py          44      8    82%
archon/harness/fs_provider.py          23      3    87%
archon/harness/manifest.py             11      0   100%
archon/harness/memory_provider.py      35      4    89%
archon/harness/parser.py               57      6    89%
archon/harness/provider.py             19      0   100%
archon/models/__init__.py               6      0   100%
archon/models/base.py                  11      1    91%
archon/models/litellm_adapter.py       40      8    80%
archon/models/mock.py                  14      1    93%
archon/models/openai_adapter.py       113     19    83%
archon/models/structured.py            36      1    97%
archon/skills/__init__.py               5      0   100%
archon/skills/definition.py             6      0   100%
archon/skills/linter.py                25      0   100%
archon/skills/loader.py                44      6    86%
archon/skills/registry.py              24      3    88%
archon/subagents/__init__.py            5      0   100%
archon/subagents/bus.py                 2      0   100%
archon/subagents/definition.py         26      0   100%
archon/subagents/dispatcher.py         43      2    95%
archon/subagents/runner.py             46      1    98%
archon/tools/__init__.py                6      0   100%
archon/tools/base.py                   13      0   100%
archon/tools/bash.py                   72      6    92%
archon/tools/decorator.py              52      4    92%
archon/tools/registry.py               24      0   100%
archon/tools/result.py                 13      0   100%
-----------------------------------------------------------------
TOTAL                                1119     96    91%
============================== 74 passed in 1.44s ==============================
```
