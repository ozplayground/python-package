# [archon] 전체 기능정의서 인덱스 (Functional Specification Index)

- **작성일자**: 2026-09-23
- **작성자**: 기획 명세 작성가 (`spec-writer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. 기능 계층 구조도 (Feature Hierarchy Tree)

`archon` 패키지의 전체 기능 구조는 하네스 기반 AI 에이전트 구동 및 안전한 실행을 담당하는 6대 모듈 계층으로 구성됩니다.

```
[1Depth: archon]
  ├── [2Depth: 코어 런타임 (Core Runtime)]
  │     ├── [3Depth: 세션 라이프사이클 및 불변 실행 컨텍스트 관리] (FUNC-CORE-001)
  │     └── [3Depth: 반응형 이벤트 메시지 버스 및 리액티브 웨이크업] (FUNC-CORE-002)
  ├── [2Depth: 하네스 시스템 (Harness System)]
  │     ├── [3Depth: 다중 소스 하네스 프로바이더 (FS / Upload / DB)] (FUNC-HARN-001)
  │     ├── [3Depth: 선언적 하네스 파서 및 마크다운 프론트매터 검증] (FUNC-HARN-002)
  │     └── [3Depth: 세션 초기화 시 하네스 동적 바인딩 및 런타임 컴파일] (FUNC-SESS-001)
  ├── [2Depth: 서브에이전트 오케스트레이터 (Subagent Orchestrator)]
  │     ├── [3Depth: 모듈러 다중 서브에이전트 비동기 동시 호출 (invoke_subagents)] (FUNC-SUB-001)
  │     └── [3Depth: 재귀 호출 깊이 한도 제어 및 순환 체인 탐지] (FUNC-SUB-002)
  ├── [2Depth: 툴 실행 엔진 (Tool Engine)]
  │     ├── [3Depth: 파이써닉 툴 레지스트리 및 선언적 @tool 데코레이터] (FUNC-TOOL-001)
  │     └── [3Depth: 디렉토리 감금 및 블랙리스트 기반 보안 Bash 실행 엔진] (FUNC-TOOL-002)
  ├── [2Depth: 스킬 시스템 (Skill System)]
  │     ├── [3Depth: 독립 스킬(Skill Isolation) 온디맨드 프로그레시브 주입] (FUNC-SKIL-001)
  │     └── [3Depth: 스킬 간 상호 참조 방지 정적 린터 및 격리 검증기] (FUNC-SKIL-002)
  └── [2Depth: 모델 어댑터 (Model Adapter)]
        ├── [3Depth: 멀티 LLM 스트리밍 및 도구 호출(Tool Call) 직렬화] (FUNC-MOD-001)
        └── [3Depth: Pydantic 기반 구조화 출력(Structured Outputs) 파서] (FUNC-MOD-002)
```

---

## 2. 전체 단위 기능 목록 요약 (Function Index)

모든 단위 기능의 상세 인터페이스, 8대 데이터 항목 명세, 비즈니스 규칙 및 예외 처리 가이드는 도메인별 상세기능정의서([`fsd/AGENT_HARNESS_SPECIFICATION.md`](./fsd/AGENT_HARNESS_SPECIFICATION.md))에 완비되어 있습니다.

| 기능 ID | 1Depth (모듈) | 2Depth (서브모듈) | 3Depth (단위기능명) | 우선순위 | 대응 요구사항 ID | 상세 명세 링크 |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `FUNC-HARN-001` | 하네스 시스템 | 프로바이더 | 다중 소스 하네스 프로바이더 (FS, Upload, DB) 및 파서 | Must | `REQ-HARN-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-harn-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-harn-001) |
| `FUNC-HARN-002` | 하네스 시스템 | 파서 | 선언적 하네스 파서 및 YAML 프론트매터 스키마 검증 | Must | `REQ-HARN-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-harn-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-harn-001) |
| `FUNC-SESS-001` | 하네스 시스템 | 세션 바인딩 | 세션 초기화 시 하네스 동적 바인딩 및 런타임 컴파일 | Must | `REQ-SESS-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001) |
| `FUNC-CORE-001` | 코어 런타임 | 세션 코어 | 세션 라이프사이클 및 불변 실행 컨텍스트 관리 | Must | `REQ-SESS-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001) |
| `FUNC-CORE-002` | 코어 런타임 | 이벤트 버스 | 반응형 이벤트 메시지 버스 및 비동기 상태 알림 | Should | `REQ-BUS-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-sub-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-sub-001) |
| `FUNC-SUB-001` | 오케스트레이터 | 병렬 호출 | 모듈러 다중 서브에이전트 비동기 동시 호출 (`invoke_subagents`) | Must | `REQ-SUB-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-sub-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-sub-001) |
| `FUNC-SUB-002` | 오케스트레이터 | 제어 정책 | 서브에이전트 재귀 깊이 제어 (`max_depth=3`) 및 순환 방지 | Must | `REQ-SUB-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-sub-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-sub-001) |
| `FUNC-TOOL-001` | 툴 엔진 | 레지스트리 | 보안 Bash 및 툴 실행 엔진 (`ToolRegistry`, `@tool`) | Must | `REQ-TOOL-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-tool-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-tool-001) |
| `FUNC-TOOL-002` | 툴 엔진 | 샌드박스 | 디렉토리 감금 및 위험 명령어 블랙리스트 차단기 | Must | `REQ-TOOL-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-tool-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-tool-001) |
| `FUNC-SKIL-001` | 스킬 시스템 | 스킬 인젝터 | 독립 스킬(Skill Isolation) 온디맨드 프로그레시브 주입 | Must | `REQ-SKIL-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-skil-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-skil-001) |
| `FUNC-SKIL-002` | 스킬 시스템 | 무결성 검증 | 스킬 간 상호 참조 방지 정적 린터 및 격리 검증기 | Must | `REQ-SKIL-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-skil-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-skil-001) |
| `FUNC-MOD-001` | 모델 어댑터 | 멀티 LLM | 멀티 LLM 스트리밍 및 도구 호출(Tool Call) 정규화 어댑터 | Must | `REQ-MOD-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001) |
| `FUNC-MOD-002` | 모델 어댑터 | 구조화 출력 | Pydantic v2 기반 구조화 출력(Structured Outputs) 역직렬화 | Must | `REQ-MOD-001` | [`fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001`](./fsd/AGENT_HARNESS_SPECIFICATION.md#func-sess-001) |

---

## 3. 상세 명세 문서 맵 (Modular FSD Map)

- [에이전트 하네스 및 오케스트레이션 상세기능정의서 (Modular FSD)](./fsd/AGENT_HARNESS_SPECIFICATION.md)
  - `FUNC-HARN-001`: 다중 소스 하네스 프로바이더 (FS, Upload, DB) 및 파서
  - `FUNC-SESS-001`: 세션 초기화 시 하네스 동적 바인딩 및 런타임 컴파일
  - `FUNC-SUB-001`: 모듈러 다중 서브에이전트 비동기 동시 호출 (`invoke_subagents`) 및 메시지 버스
  - `FUNC-TOOL-001`: 보안 Bash 및 툴 실행 엔진 (`ToolRegistry`, `@tool`)
  - `FUNC-SKIL-001`: 독립 스킬(Skill Isolation) 온디맨드 프로그레시브 주입
