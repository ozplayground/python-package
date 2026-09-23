# Skill Governance & Progressive Injection Package (`archon.skills`)

## 1. 모듈 개요 및 책임 (Module Scope & Responsibility)

`archon.skills`는 재사용 가능한 도메인 지침(`.agents/skills/*/SKILL.md`)을 관리하고, **스킬 독립성 원칙 (Skill Isolation Principle)**을 강제하며, 서브에이전트가 필요로 하는 시점에만 점진적으로 컨텍스트를 주입(Progressive Disclosure)하는 역할을 담당합니다.

- **스킬 독립성 원칙 (Rule 5)**: 모든 스킬은 원자적(Atomic)이며 직교(Orthogonal)해야 합니다. 스킬 파일 내부에서 다른 스킬의 이름이나 경로를 참조하는 행위는 엄격히 금지됩니다.
- **정적 린터 (`SkillLinter`)**: 하네스 파싱 시 모든 스킬 본문을 검사하여 타 스킬 언급이나 상대 경로 인클루드 발견 시 `SkillIsolationError`를 발생시키며 세션 로드를 거부(Zero Tolerance)합니다.
- **온디맨드 프로그레시브 주입**: 서브에이전트 명세에 명시된 필수 스킬(`required_skills`)만 해당 서브에이전트 실행 시점에 시스템 프롬프트에 주입되어 프롬프트 토큰 낭비를 원천 차단합니다.

---

## 2. 구현 대상 요구사항 (Implemented Requirements)

- **`REQ-SKIL-001`**: 독립 스킬 온디맨드 프로그레시브 주입 및 정적 린터 (`FUNC-SKIL-001`, `FUNC-SKIL-002`)

---

## 3. 공개 클래스 및 인터페이스 목록 (Public Classes & Interfaces)

| 클래스/인터페이스 | 설명 | 핵심 메서드 / 속성 |
| :--- | :--- | :--- |
| `SkillDefinition` | 개별 스킬 명세 모델 | `name`, `description`, `instructions` |
| `SkillRegistry` | 세션 내 가용 스킬 카탈로그 | `register()`, `get()`, `get_prompt_injection(skill_names)` |
| `SkillLoader` | 디렉토리 탐색 및 파싱 로더 | `load_directory()`, `validate_isolation()` |
| `SkillLinter` | 스킬 독립성 정적 린터 | `lint(skill_content, registered_skill_names)` |

---

## 4. 타 모듈과의 의존성 제약 (Dependency Rules)

- **스킬 간 결합도 제로**: 스킬 A가 스킬 B를 임포트하거나 의존할 수 없습니다. 두 스킬이 모두 필요한 경우 상위 서브에이전트가 `required_skills: [skill_a, skill_b]`로 각각 독립 주입받아야 합니다.
- **하향 의존 원칙**: 스킬 모듈은 툴이나 세션 런타임에 직접 의존하지 않고 순수 마크다운 지침 텍스트를 공급합니다.

---

## 5. 단위 테스트 실행 가이드 및 주요 엣지 케이스 (Testing Guide)

```bash
# Skills 모듈 관련 테스트 실행
pytest tests/test_skills.py tests/test_skill_linter.py -v
```

### 주요 검증 엣지 케이스
- **타 스킬 이름 직접 참조 감지**: 스킬 본문에서 다른 등록된 스킬명을 언급할 경우 라인 번호와 함께 `SkillIsolationError` 발생.
- **상대 경로 인클루드 차단**: `../caching/SKILL.md` 등 파일 상대 경로 포함 시 즉시 거절.
- **점진적 주입 검증**: 요구된 스킬 지침만 렌더링되고 미요구 스킬의 프롬프트 유입 0건 확인.
