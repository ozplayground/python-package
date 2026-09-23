# Harness System Package (`archon.harness`)

## 1. 모듈 개요 및 책임 (Module Scope & Responsibility)

`archon.harness`는 선언적 에이전트 거버넌스(`AGENTS.md`, `.agents/rules/`, `.agents/skills/`, `.agents/subagents/`)를 다중 저장소로부터 로드하고, YAML 프론트매터 및 마크다운 본문을 파싱하여 불변의 `HarnessManifest` 스냅샷을 생성하는 책임을 갖습니다.

- **다중 소스 지원 (Multi-Source Providers)**: 로컬 파일시스템(`FS`), 인메모리 압축 바이너리(`Upload`), 데이터베이스(`DB`) 소스를 일관된 인터페이스로 추상화합니다.
- **ZipSlip 경로 탈출 방어**: 압축 해제 시 `../` 또는 파일시스템 절대 경로를 포함한 악의적 압축 엔트리를 런타임에 사전 차단합니다.
- **최우선 헌법 강제**: `AGENTS.md` 파일을 파이프라인의 최고 거버넌스 헌법으로 규정하여 런타임에 최우선 시스템 지시문으로 결합합니다.

---

## 2. 구현 대상 요구사항 (Implemented Requirements)

- **`REQ-HARN-001`**: 다중 소스 하네스 프로바이더 및 파서 (`FUNC-HARN-001`, `FUNC-HARN-002`)
- **`REQ-SESS-001`**: 세션 단위 하네스 동적 바인딩 및 런타임 컴파일 (`FUNC-SESS-001`)

---

## 3. 공개 클래스 및 인터페이스 목록 (Public Classes & Interfaces)

| 클래스/인터페이스 | 설명 | 핵심 메서드 / 팩토리 |
| :--- | :--- | :--- |
| `HarnessProvider` | 하네스 프로바이더 추상 기본 클래스 | `load()`, `from_fs()`, `from_upload()`, `from_db()` |
| `FileSystemHarnessProvider` | 로컬 디렉토리 탐색 기반 로더 | `base_path`, `load()` |
| `InMemoryHarnessProvider` | Zip 바이트 스트림 인메모리 로더 및 ZipSlip 가드 | `archive_bytes`, `load()` |
| `DatabaseHarnessProvider` | RDBMS/NoSQL 테넌트 하네스 로더 | `records`, `db_session`, `tenant_id`, `load()` |
| `HarnessParser` | 마크다운 AST 및 YAML 프론트매터 파서 | `parse_frontmatter()`, `parse_files()` |
| `HarnessManifest` | 불변 하네스 명세 스냅샷 DTO | `constitution`, `rules`, `skills`, `subagents`, `metadata` |

---

## 4. 타 모듈과의 의존성 제약 (Dependency Rules)

- **단방향 의존성 준수**: `harness`는 모델이나 툴 구현체에 의존하지 않으며, 오직 `skills.definition` 및 `subagents.definition`의 명세 모델만을 참조합니다.
- **불변 스냅샷 방출**: 상위 세션 엔진으로는 오직 변경 불가능한 Pydantic Frozen 모델인 `HarnessManifest`만 방출합니다.

---

## 5. 단위 테스트 실행 가이드 및 주요 엣지 케이스 (Testing Guide)

```bash
# Harness 모듈 관련 테스트 실행
pytest tests/test_harness.py tests/test_harness_factories_and_security.py -v
```

### 주요 검증 엣지 케이스
- **ZipSlip 공격 차단**: `../../etc/passwd`, `sub/../../escape.md`, `..\..\windows` 등 상대/절대 탈출 경로 감지 시 `HarnessSecurityError` 발생.
- **필수 헌법 누락**: `AGENTS.md` 누락 시 `HarnessParseError` 발생.
- **프론트매터 문법 에러**: YAML 구문 불량 시 라인 번호와 원인을 명시한 `HarnessParseError` 발생.
- **초고속 파싱 지연**: 파싱 및 스냅샷 생성 지연 $\le 20\text{ms}$ 보장.
