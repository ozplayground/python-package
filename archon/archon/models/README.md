# Model Adapters & Structured Outputs Package (`archon.models`)

## 1. 모듈 개요 및 책임 (Module Scope & Responsibility)

`archon.models`는 다양한 LLM 공급자(OpenAI, Anthropic, Gemini, 로컬 vLLM 등)와의 통신을 표준화하고, 스트리밍 토큰 수신, 도구 호출(Tool Call) 역직렬화, 그리고 Pydantic v2 기반의 구조화 출력(Structured Outputs) 파싱을 전담합니다.

- **공급자 중립성**: 상위 에이전트는 특정 벤더 API 규격에 결합되지 않고 통일된 `StepResult`와 스트리밍 비동기 제너레이터를 사용합니다.
- **결정론적 모의 어댑터 (`MockModelAdapter`)**: 외부 네트워크 호출 및 API 비용 없이 단위 테스트를 빠르고 안정적으로 실행할 수 있도록 사전문답(Canned Responses) FIFO 매핑을 제공합니다.
- **Full Jitter 지수 백오프**: 일시적 장애(429 Rate Limit, 5xx 에러) 수신 시 최대 3회 지수 백오프 재시도를 자동 수행합니다.
- **Pydantic v2 구조화 출력 파서 (`StructuredOutputParser`)**: LLM 생성 텍스트에서 마크다운 코드 블록(```json)을 안전하게 추출하고 Rust 코어 기반 고속 역직렬화 및 엄격 스키마 검증을 수행합니다.

---

## 2. 구현 대상 요구사항 (Implemented Requirements)

- **`REQ-MOD-001`**: 멀티 LLM 모델 어댑터 및 스트리밍 처리 (`FUNC-MOD-001`, `FUNC-MOD-002`)

---

## 3. 공개 클래스 및 인터페이스 목록 (Public Classes & Interfaces)

| 클래스/인터페이스 | 설명 | 핵심 메서드 / 속성 |
| :--- | :--- | :--- |
| `BaseModelAdapter` | 모델 어댑터 추상 기본 클래스 | `generate()`, `async_generate()`, `stream_generate()` |
| `MockModelAdapter` | 결정론적 오프라인 테스트용 모의 어댑터 | `canned_responses`, `calls`, `generate()` |
| `OpenAIAdapter` | OpenAI ChatCompletions 및 도구 호출 어댑터 | `api_key`, `base_url`, `model_name`, `stream_generate()` |
| `LiteLLMAdapter` | 100+ 멀티 LLM 통합 라우팅 어댑터 | `model_name`, `provider`, `async_generate()` |
| `StructuredOutputParser` | Pydantic v2 구조화 출력 파서 | `parse()`, `strip_markdown_fences()`, `get_strict_json_schema()` |

---

## 4. 타 모듈과의 의존성 제약 (Dependency Rules)

- **출력 정규화**: 어댑터는 모델의 원시 응답을 `archon.core.step.StepResult`로 표준화하여 상위 계층에 전달합니다.
- **Fast-Fail 원칙**: 인증 실패(401, 403) 시에는 지수 백오프 재시도를 생략하고 즉시 `ModelAuthenticationError`로 조기 종료합니다.

---

## 5. 단위 테스트 실행 가이드 및 주요 엣지 케이스 (Testing Guide)

```bash
# Models 모듈 관련 테스트 실행
pytest tests/test_model_adapters.py -v
```

### 주요 검증 엣지 케이스
- **HTTPX MockTransport 기반 OpenAI 통신**: 네트워크 없이 모의 HTTP 핸들러로 200 OK, 401 Auth Error, 500 Retry 후 성공 시나리오 검증.
- **SSE 스트리밍 토큰 조합**: `data: {"choices": [{"delta": {"content": "..."}}]}` 스트림 토큰 정규화 검증.
- **구조화 출력 파싱 에러 추적성**: 필수 필드 결손 또는 잘못된 JSON 응답 시 원본 텍스트를 보존한 `ModelResponseValidationError` 발생.
