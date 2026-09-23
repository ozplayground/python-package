# [archon] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-23
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.2 (도메인별 모듈러 FSD 완전 분리 개정판)
- **상태**: Approved

---

## 1. 요구사항 기반 기능 계층 구조도 (Requirement-to-Function Hierarchy Tree)

`archon`의 기능 구조는 PRD에 정의된 핵심 요구사항(`REQ-xxx`)을 기준으로 단위 기능(`FUNC-xxx`)이 1:1 또는 1:N으로 명확하게 추적되도록 구성되어 있습니다.

```
[archon 요구사항-기능 추적 구조도]
  ├── [REQ-HARN-001: 다중 소스 하네스 프로바이더 및 파서]
  │     ├── ➔ [FUNC-HARN-001] 다중 소스 하네스 프로바이더 (FS / Upload / DB)
  │     └── ➔ [FUNC-HARN-002] 선언적 하네스 파서 및 YAML 프론트매터 스키마 검증
  ├── [REQ-SESS-001: 세션 단위 하네스 동적 바인딩 및 런타임 컴파일]
  │     ├── ➔ [FUNC-SESS-001] 세션 초기화 시 하네스 동적 바인딩 및 런타임 컴파일
  │     └── ➔ [FUNC-CORE-001] 세션 라이프사이클 및 불변 실행 컨텍스트 관리
  ├── [REQ-SUB-001: 모듈러 다중 서브에이전트 비동기 동시 호출]
  │     ├── ➔ [FUNC-SUB-001] 모듈러 다중 서브에이전트 비동기 동시 호출 (invoke_subagents)
  │     └── ➔ [FUNC-SUB-002] 서브에이전트 재귀 깊이 제어 (max_depth=3) 및 순환 방지
  ├── [REQ-TOOL-001: 보안 Bash 및 툴 실행 엔진]
  │     ├── ➔ [FUNC-TOOL-001] 파이써닉 툴 레지스트리 및 선언적 @tool 데코레이터
  │     └── ➔ [FUNC-TOOL-002] 디렉토리 감금 및 블랙리스트 기반 보안 Bash 실행 엔진
  ├── [REQ-SKIL-001: 독립 스킬(Skill Isolation) 온디맨드 프로그레시브 주입]
  │     ├── ➔ [FUNC-SKIL-001] 독립 스킬(Skill Isolation) 온디맨드 프로그레시브 주입
  │     └── ➔ [FUNC-SKIL-002] 스킬 간 상호 참조 방지 정적 린터 및 격리 검증기
  ├── [REQ-MOD-001: 멀티 LLM 모델 어댑터 및 구조화 출력]
  │     ├── ➔ [FUNC-MOD-001] 멀티 LLM 스트리밍 및 도구 호출(Tool Call) 정규화 어댑터
  │     └── ➔ [FUNC-MOD-002] Pydantic v2 기반 구조화 출력(Structured Outputs) 역직렬화
  └── [REQ-BUS-001: 반응형 이벤트 메시지 버스]
        └── ➔ [FUNC-CORE-002] 반응형 이벤트 메시지 버스 및 비동기 상태 알림
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

모든 단위 기능은 6대 도메인별 모듈러 상세기능정의서(`fsd/*.md`)에 상위 `REQ-xxx` 인수 기준(정상/예외/검증) 바인딩을 포함한 7대 상세 명세 및 8대 표준 컬럼 데이터 명세가 완비되어 있습니다.

| 기능 ID | 1Depth (모듈) | 2Depth (서브모듈) | 3Depth (단위기능명) | 우선순위 | 대응 요구사항 ID | 상세 명세 링크 |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `FUNC-HARN-001` | 하네스 시스템 | 프로바이더 | 다중 소스 하네스 프로바이더 (FS, Upload, DB) 및 로더 | Must | `REQ-HARN-001` | [`fsd/HARNESS_SPECIFICATION.md#func-harn-001`](./fsd/HARNESS_SPECIFICATION.md#func-harn-001) |
| `FUNC-HARN-002` | 하네스 시스템 | 파서 | 선언적 하네스 파서 및 YAML 프론트매터 스키마 검증 | Must | `REQ-HARN-001` | [`fsd/HARNESS_SPECIFICATION.md#func-harn-002`](./fsd/HARNESS_SPECIFICATION.md#func-harn-002) |
| `FUNC-SESS-001` | 세션/코어 | 세션 바인딩 | 세션 초기화 시 하네스 동적 바인딩 및 런타임 컴파일 | Must | `REQ-SESS-001` | [`fsd/SESSION_CORE_SPECIFICATION.md#func-sess-001`](./fsd/SESSION_CORE_SPECIFICATION.md#func-sess-001) |
| `FUNC-CORE-001` | 세션/코어 | 세션 코어 | 세션 라이프사이클 및 불변 실행 컨텍스트 관리 | Must | `REQ-SESS-001` | [`fsd/SESSION_CORE_SPECIFICATION.md#func-core-001`](./fsd/SESSION_CORE_SPECIFICATION.md#func-core-001) |
| `FUNC-CORE-002` | 세션/코어 | 이벤트 버스 | 반응형 이벤트 메시지 버스 및 비동기 상태 알림 | Should | `REQ-BUS-001` | [`fsd/SESSION_CORE_SPECIFICATION.md#func-core-002`](./fsd/SESSION_CORE_SPECIFICATION.md#func-core-002) |
| `FUNC-SUB-001` | 서브에이전트 | 병렬 오케스트레이션 | 모듈러 다중 서브에이전트 비동기 동시 호출 (`invoke_subagents`) | Must | `REQ-SUB-001` | [`fsd/SUBAGENT_SPECIFICATION.md#func-sub-001`](./fsd/SUBAGENT_SPECIFICATION.md#func-sub-001) |
| `FUNC-SUB-002` | 서브에이전트 | 깊이 제어 | 서브에이전트 재귀 깊이 제어 (`max_depth=3`) 및 순환 방지 | Must | `REQ-SUB-001` | [`fsd/SUBAGENT_SPECIFICATION.md#func-sub-002`](./fsd/SUBAGENT_SPECIFICATION.md#func-sub-002) |
| `FUNC-TOOL-001` | 툴 엔진 | 레지스트리 | 파이써닉 툴 레지스트리 및 선언적 `@tool` 데코레이터 | Must | `REQ-TOOL-001` | [`fsd/TOOL_ENGINE_SPECIFICATION.md#func-tool-001`](./fsd/TOOL_ENGINE_SPECIFICATION.md#func-tool-001) |
| `FUNC-TOOL-002` | 툴 엔진 | 샌드박스 | 디렉토리 감금 및 블랙리스트 기반 보안 Bash 실행 엔진 | Must | `REQ-TOOL-001` | [`fsd/TOOL_ENGINE_SPECIFICATION.md#func-tool-002`](./fsd/TOOL_ENGINE_SPECIFICATION.md#func-tool-002) |
| `FUNC-SKIL-001` | 스킬 시스템 | 스킬 인젝터 | 독립 스킬(Skill Isolation) 온디맨드 프로그레시브 주입 | Must | `REQ-SKIL-001` | [`fsd/SKILL_SYSTEM_SPECIFICATION.md#func-skil-001`](./fsd/SKILL_SYSTEM_SPECIFICATION.md#func-skil-001) |
| `FUNC-SKIL-002` | 스킬 시스템 | 무결성 검증 | 스킬 간 상호 참조 방지 정적 린터 및 격리 검증기 | Must | `REQ-SKIL-001` | [`fsd/SKILL_SYSTEM_SPECIFICATION.md#func-skil-002`](./fsd/SKILL_SYSTEM_SPECIFICATION.md#func-skil-002) |
| `FUNC-MOD-001` | 모델 어댑터 | 멀티 LLM | 멀티 LLM 스트리밍 및 도구 호출(Tool Call) 정규화 어댑터 | Must | `REQ-MOD-001` | [`fsd/MODEL_ADAPTER_SPECIFICATION.md#func-mod-001`](./fsd/MODEL_ADAPTER_SPECIFICATION.md#func-mod-001) |
| `FUNC-MOD-002` | 모델 어댑터 | 구조화 출력 | Pydantic v2 기반 구조화 출력(Structured Outputs) 역직렬화 | Must | `REQ-MOD-001` | [`fsd/MODEL_ADAPTER_SPECIFICATION.md#func-mod-002`](./fsd/MODEL_ADAPTER_SPECIFICATION.md#func-mod-002) |

---

## 3. 요구사항 추적성 매트릭스 (REQ-FUNC Traceability Matrix)

PRD에 정의된 인수 기준(정상/예외/검증 조건)과 6대 도메인 상세기능명세서(FSD) 및 테스트 타깃의 100% 대응 관계를 입증하는 전면 추적성 매트릭스입니다.

| 요구사항 ID (REQ) | 요구사항 명칭 | 우선순위 | 대응 단위기능 ID (FUNC) | 기능 명칭 | 인수 기준 검증 매핑 | 상세 FSD 앵커 링크 |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| `REQ-HARN-001` | 다중 소스 하네스 프로바이더 및 파서 | Must | `FUNC-HARN-001`<br/>`FUNC-HARN-002` | 다중 소스 하네스 로더 및 마크다운/YAML 정규화 파서 | FS/Zip/DB 3종 소스 로드 $\le 10\text{ms}$, ZipSlip 차단, 스키마 유효성 검증 | [`FSD: HARNESS`](./fsd/HARNESS_SPECIFICATION.md) |
| `REQ-SESS-001` | 세션 하네스 동적 바인딩 & 컴파일 | Must | `FUNC-SESS-001`<br/>`FUNC-CORE-001` | 세션 격리 런타임 컴파일 및 라이프사이클 관리 | 테넌트 격리 컨텍스트, 복제 레지스트리, 세션 타임아웃(600s) 및 자식 태스크 취소 | [`FSD: SESSION_CORE`](./fsd/SESSION_CORE_SPECIFICATION.md) |
| `REQ-SUB-001` | 모듈러 서브에이전트 비동기 동시 호출 | Must | `FUNC-SUB-001`<br/>`FUNC-SUB-002` | `invoke_subagents` 병렬 오케스트레이션 및 깊이 제어 | `asyncio.gather` 병렬 디스패치, 재귀 깊이 3단계 한도, 순환 체인 차단, 부분 성공 보존 | [`FSD: SUBAGENT`](./fsd/SUBAGENT_SPECIFICATION.md) |
| `REQ-TOOL-001` | 보안 Bash 및 툴 실행 엔진 | Must | `FUNC-TOOL-001`<br/>`FUNC-TOOL-002` | 툴 레지스트리 및 샌드박스 Bash 실행기 | `@tool` 스키마 자동 생성, 작업 디렉토리 감금, 위험 명령어 블랙리스트 차단, `os.killpg` | [`FSD: TOOL_ENGINE`](./fsd/TOOL_ENGINE_SPECIFICATION.md) |
| `REQ-SKIL-001` | 독립 스킬 온디맨드 프로그레시브 주입 | Must | `FUNC-SKIL-001`<br/>`FUNC-SKIL-002` | 스킬 온디맨드 인젝터 및 상호참조 차단 정적 린터 | 스킬 간 상호참조 정적 검증 거부(`SkillIsolationViolationError`), 선언 스킬만 점진 주입 | [`FSD: SKILL_SYSTEM`](./fsd/SKILL_SYSTEM_SPECIFICATION.md) |
| `REQ-MOD-001` | 멀티 LLM 어댑터 및 구조화 출력 | Must | `FUNC-MOD-001`<br/>`FUNC-MOD-002` | 멀티 LLM 스트리밍 및 Pydantic v2 구조화 출력 파서 | OpenAI/Anthropic 규격 직렬화, Pydantic v2 `BaseModel` 파싱, 3회 Full Jitter 재시도 | [`FSD: MODEL_ADAPTER`](./fsd/MODEL_ADAPTER_SPECIFICATION.md) |
| `REQ-BUS-001` | 반응형 이벤트 메시지 버스 | Should | `FUNC-CORE-002` | 세션 내 반응형 비동기 메시지 버스 | 1:1 메시지 전달, 이벤트 브로드캐스트, 리액티브 웨이크업, FIFO 1,000건 유실 0건 | [`FSD: SESSION_CORE`](./fsd/SESSION_CORE_SPECIFICATION.md#func-core-002) |

---

## 4. 6대 도메인별 모듈러 상세기능정의서 맵 (Modular FSD Map)

`archon`의 FSD는 단일 거대 문서를 탈피하여 도메인 책임 단위로 완벽히 분리된 6개의 모듈러 FSD로 구성됩니다:

1. **[하네스 시스템 상세기능정의서 (Harness System Modular FSD)](./fsd/HARNESS_SPECIFICATION.md)**
   - `FUNC-HARN-001` (대응 `REQ-HARN-001`): 다중 소스 하네스 프로바이더 (FS, Upload, DB) 및 로더
   - `FUNC-HARN-002` (대응 `REQ-HARN-001`): 선언적 하네스 파서 및 YAML 프론트매터 스키마 검증
2. **[세션 및 코어 런타임 상세기능정의서 (Session & Core Modular FSD)](./fsd/SESSION_CORE_SPECIFICATION.md)**
   - `FUNC-SESS-001` (대응 `REQ-SESS-001`): 세션 초기화 시 하네스 동적 바인딩 및 런타임 컴파일
   - `FUNC-CORE-001` (대응 `REQ-SESS-001`): 세션 라이프사이클 및 불변 실행 컨텍스트 관리
   - `FUNC-CORE-002` (대응 `REQ-BUS-001`): 반응형 이벤트 메시지 버스 및 비동기 상태 알림
3. **[서브에이전트 오케스트레이션 상세기능정의서 (Subagent Modular FSD)](./fsd/SUBAGENT_SPECIFICATION.md)**
   - `FUNC-SUB-001` (대응 `REQ-SUB-001`): 모듈러 다중 서브에이전트 비동기 동시 호출 (`invoke_subagents`)
   - `FUNC-SUB-002` (대응 `REQ-SUB-001`): 서브에이전트 재귀 깊이 제어 (`max_depth=3`) 및 순환 체인 방지
4. **[툴 엔진 상세기능정의서 (Tool Engine Modular FSD)](./fsd/TOOL_ENGINE_SPECIFICATION.md)**
   - `FUNC-TOOL-001` (대응 `REQ-TOOL-001`): 파이써닉 툴 레지스트리 및 선언적 `@tool` 데코레이터
   - `FUNC-TOOL-002` (대응 `REQ-TOOL-001`): 디렉토리 감금 및 블랙리스트 기반 보안 Bash 실행 엔진
5. **[스킬 시스템 상세기능정의서 (Skill System Modular FSD)](./fsd/SKILL_SYSTEM_SPECIFICATION.md)**
   - `FUNC-SKIL-001` (대응 `REQ-SKIL-001`): 독립 스킬(Skill Isolation) 온디맨드 프로그레시브 주입
   - `FUNC-SKIL-002` (대응 `REQ-SKIL-001`): 스킬 간 상호 참조 방지 정적 린터 및 격리 검증기
6. **[모델 어댑터 상세기능정의서 (Model Adapter Modular FSD)](./fsd/MODEL_ADAPTER_SPECIFICATION.md)**
   - `FUNC-MOD-001` (대응 `REQ-MOD-001`): 멀티 LLM 스트리밍 및 도구 호출(Tool Call) 정규화 어댑터
   - `FUNC-MOD-002` (대응 `REQ-MOD-001`): Pydantic v2 기반 구조화 출력(Structured Outputs) 역직렬화
