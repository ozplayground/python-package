# Archon: Harness-governed Multi-Agent Orchestration & Execution Engine SDK

`archon`은 마크다운 기반 하네스 거버넌스(`AGENTS.md`, `.agents/`)를 퍼스트 클래스로 수용하고, 세션 단위 다중 소스(로컬 파일시스템, Zip 업로드, 데이터베이스) 동적 바인딩과 안전한 서브에이전트 비동기 동시 오케스트레이션을 제공하는 파이썬 에이전트 SDK입니다.

---

## 1. 핵심 아키텍처 및 6대 모듈 구성

`archon`은 책임과 경계가 명확히 분리된 6대 서브패키지로 구성됩니다:

1. **`core/`**: 세션 라이프사이클 격리(`AgentSession`), 불변 실행 컨텍스트(`ExecutionContext`), 턴별 실행 결과(`StepResult`), 반응형 이벤트 메시지 버스(`MessageBus`).
2. **`harness/`**: 다중 소스 하네스 로더(`HarnessProvider`: `FileSystemHarnessProvider`, `InMemoryHarnessProvider`, `DatabaseHarnessProvider`), 마크다운 AST 및 YAML 프론트매터 파서(`HarnessParser`), 불변 명세 스냅샷(`HarnessManifest`).
3. **`subagents/`**: 복수 서브에이전트 비동기 병렬 호출(`invoke_subagents`, `SubagentDispatcher`), 격리 실행기(`SubagentRunner`), 동시성 제어 세마포어(Max 10), 재귀 깊이(`max_depth=3`) 및 순환 체인 차단.
4. **`tools/`**: 도구 추상화(`BaseTool`), 보안 샌드박스 셸(`BashTool`: 디렉토리 감금, 위험 명령어 블랙리스트, `os.setsid`/`os.killpg` 좀비 방지, 1MB 버퍼 절삭), 세션 격리 레지스트리(`ToolRegistry`), 선언적 데코레이터(`@tool`).
5. **`skills/`**: 스킬 명세(`SkillDefinition`), 카탈로그(`SkillRegistry`), 로더(`SkillLoader`), 스킬 독립성 원칙 정적 검증기(`SkillLinter`, Rule 5 상호 참조 원천 차단).
6. **`models/`**: 모델 어댑터 인터페이스(`BaseModelAdapter`), 오프라인 결정론적 테스트용(`MockModelAdapter`), OpenAI 프로토콜(`OpenAIAdapter`), 멀티 벤더 연동(`LiteLLMAdapter`), Pydantic v2 구조화 출력 파서(`StructuredOutputParser`).

---

## 2. 빠른 시작 (Quick Start)

### 2.1 세션 생성 및 메인 에이전트 실행

```python
from pathlib import Path
from archon import create_session
from archon.models import MockModelAdapter
from archon.tools import tool

# 1. 커스텀 도구 정의
@tool(name="calculate_tax", description="부가가치세를 계산합니다.")
def calculate_tax(amount: int, rate: float = 0.1) -> int:
    return int(amount * rate)

# 2. 세션 동적 바인딩 및 초기화
session = create_session(
    harness=Path("./my_project_harness"),
    model=MockModelAdapter(),
    custom_tools=[calculate_tax],
)

# 3. 비동기 턴 실행
result = await session.async_run("주문 금액 10,000원에 대한 세금을 계산해줘.")
print(result.text)

# 4. 세션 리소스 정리
session.close()
```

### 2.2 다중 서브에이전트 비동기 병렬 호출

```python
from archon.subagents import SubagentRequest

requests = [
    SubagentRequest(subagent_name="backend_engineer", prompt="API 엔드포인트를 설계하세요."),
    SubagentRequest(subagent_name="frontend_engineer", prompt="UI 컴포넌트를 설계하세요."),
]

# asyncio.gather 기반 병렬 실행 (최대 10개 세마포어, max_depth=3 가드)
results = await session.invoke_subagents(requests)

for r in results:
    print(f"[{r.subagent_name}] Success: {r.is_success} | Output: {r.output}")
```

---

## 3. 테스트 실행 가이드

가상환경 및 `pytest`를 통해 전체 단위, 통합, 보안, 동시성 스트레스 테스트를 실행합니다:

```bash
# 전체 테스트 및 커버리지 측정
pytest --cov=archon --cov-report=term-missing -v

# 100개 코루틴 동시 세션/서브에이전트 부하 스트레스 검증
pytest tests/test_concurrency_stress.py -v
```

---

## 4. 라이선스

MIT License.
