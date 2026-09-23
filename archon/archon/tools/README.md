# Tool Engine & Security Sandbox Package (`archon.tools`)

## 1. 모듈 개요 및 책임 (Module Scope & Responsibility)

`archon.tools`는 에이전트가 사용하는 도구의 등록, 메타데이터 자동 추출, 세션별 격리 복제, 그리고 보안 Bash 서브프로세스 샌드박스 실행을 전담합니다.

- **보안 Bash 샌드박스 (`BashTool`)**:
  - **작업 디렉토리 감금 (Directory Jail)**: `working_directory` 상위 경로 탈출(`cd /`, `cd ../..`) 원천 차단.
  - **위험 명령어 블랙리스트**: `rm -rf /`, `sudo`, `su`, `mkfs`, `dd`, `shutdown`, `reboot`, `:(){ :|:& };:`(포크폭탄) 등 파괴적 명령어 사전 차단 (`ToolSecurityError`).
  - **프로세스 그룹 분리 및 강제 회수**: `preexec_fn=os.setsid` 기반 독립 PGID 부여 및 타임아웃 시 `os.killpg(SIGKILL)` 전파로 좀비 프로세스 방지.
  - **메모리 버퍼 절삭**: 출력 버퍼 1MB 초과 시 안전 절삭 및 `[TRUNCATED: Output exceeded 1MB]` 표기.
- **선언적 `@tool` 데코레이터**: 파이썬 일반 함수의 타입 힌트와 Docstring을 분석하여 OpenAI 호환 JSON Schema 자동 추출.
- **세션 격리 도구 레지스트리 (`ToolRegistry`)**: 세션 생성 시 딥클론(`clone()`)되어 특정 세션의 툴 변경이 타 세션으로 번지지 않음.

---

## 2. 구현 대상 요구사항 (Implemented Requirements)

- **`REQ-TOOL-001`**: 보안 Bash 및 툴 실행 엔진 (`FUNC-TOOL-001`, `FUNC-TOOL-002`)

---

## 3. 공개 클래스 및 인터페이스 목록 (Public Classes & Interfaces)

| 클래스/인터페이스 | 설명 | 핵심 메서드 / 속성 |
| :--- | :--- | :--- |
| `BaseTool` | 도구 추상 기본 클래스 | `execute()`, `to_openai_schema()`, `name`, `parameters_schema` |
| `BashTool` | 다층 샌드박스 Bash 셸 실행 도구 | `execute(command)`, `working_directory`, `timeout_seconds`, `blacklist_patterns` |
| `ToolRegistry` | 세션 격리 도구 카탈로그 | `register()`, `register_func()`, `get()`, `get_schemas()`, `clone()` |
| `@tool` | 함수 기반 도구 선언 데코레이터 | `@tool(name="...", description="...")` |
| `ToolExecutionResult` | 도구 실행 결과 표준 DTO | `exit_code`, `stdout`, `stderr`, `error`, `is_truncated`, `duration_ms` |

---

## 4. 타 모듈과의 의존성 제약 (Dependency Rules)

- **독립성 원칙**: `tools`는 순수한 실행 엔진으로서 상위 `core`나 `subagents`에 역의존하지 않습니다.
- **타입 안정성**: JSON Schema 변환 시 기본 내장 타입(int, float, str, bool, list, dict)을 정규화 매핑합니다.

---

## 5. 단위 테스트 실행 가이드 및 주요 엣지 케이스 (Testing Guide)

```bash
# Tools 모듈 관련 테스트 실행
pytest tests/test_tools.py -v
```

### 주요 검증 엣지 케이스
- **위험 명령어 10종 이상 모의 주입**: `rm -rf /`, `sudo`, `dd`, `mkfs`, 포크폭탄 등 100% 차단 검증.
- **디렉토리 탈출 시도 차단**: `cd / && ls`, `cd ../../` 등 Jail 외부 참조 시 `ToolSecurityError` 발생.
- **프로세스 그룹 타임아웃 종료**: 5초 슬립 명령에 0.2초 타임아웃 부여 시 `exit_code=124` 및 프로세스 정리.
- **1MB 출력 절삭**: 1.2MB 출력 생성 스크립트 실행 시 1MB 지점에서 절삭 플래그(`is_truncated=True`) 설정.
