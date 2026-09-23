# [courier] 통합 QA 테스트 계획서 (QA Test Plan)

- **작성일자**: 2026-09-22
- **작성자**: 품질 보증 엔지니어 (`qa-engineer`)
- **문서 버전**: v1.1 (Humanizer 지침 기반 전면 개정)
- **상태**: **Approved**

---

## 1. 테스트 목적 및 중점 검증 영역 (Focus Areas)

외부 마이크로서비스 및 서드파티 API와의 HTTP 통신은 분산 시스템 장애의 가장 흔한 진원지입니다. 네트워크 순간 단절(Flapping), 원격지 지연 누적으로 인한 스레드 풀 고갈, 비정상 대용량 페이로드 수신에 따른 메모리 부족(OOM), 예외 발생 시 소켓 미반환 등은 단순 기능 테스트에서는 드러나지 않지만 실 서비스 환경에서는 치명적인 전체 장애를 유발합니다.

본 테스트 계획서는 `courier` 라이브러리가 이러한 네트워크 장애 상황에서도 애플리케이션의 가용성을 유지하고 안전하게 회복할 수 있는지를 확인하기 위해 수립되었습니다. 형식적인 200 OK 나열을 지양하고, 실제 운영에서 문제를 일으키기 쉬운 다음 4대 핵심 영역을 집중 검증합니다:

1. **지수 백오프 및 재시도 분산 (Full Jitter & Thundering Herd 방어)**:
   - 일시적 장애(503, 429) 시 모든 클라이언트가 동시에 재시도하여 대상 서버를 마비시키는 '재시도 폭풍'을 AWS Full Jitter 공식으로 분산시키는지 검증합니다.
   - 서버가 `Retry-After: 3600`과 같이 과도한 대기를 요구할 때, 워커 스레드가 블로킹되어 서비스가 멈추지 않도록 30초 상한선(`max_backoff_seconds`)에서 즉시 차단(Fail-Fast)하는지 확인합니다.
2. **고동시성 커넥션 풀 경합 및 리소스 누수 차단 (Zero Socket Leak)**:
   - 50개 스레드와 100개 코루틴이 동시에 몰리는 상황에서 커넥션 풀(`httpx.Limits`)이 교착 상태(Deadlock)에 빠지지 않고 대기 큐를 통해 정상 소화되는지 검증합니다.
   - 클라이언트 인스턴스 해제(`close`, `aclose`) 및 프로세스 종료(`atexit`) 시점에 열려 있는 소켓이나 파일 디스크립터 누수가 없는지 확인합니다.
3. **비정상 응답 방어 및 메모리 안전망 (1MB Truncation Guard)**:
   - 외부 서버의 오동작으로 1MB 이상의 비정상 데이터가 유입될 때 무제한 버퍼링으로 OOM 크래시가 발생하는 것을 막고, 최대 1MB까지만 절삭 수신하는지 검증합니다.
4. **Result 패턴 및 DTO 런타임 역직렬화 무결성**:
   - HTTP 통신 결과를 예외 대신 `ApiResponse[T]` 제네릭 컨테이너로 감싸고, Pydantic v2 모델로 변환(`into`)할 때 스키마 불일치가 발생해도 애플리케이션이 크래시되지 않고 명확한 에러 정보를 제공하는지 확인합니다.

---

## 2. 테스트 환경 및 제약 조건

- **런타임 및 플랫폼**:
  - Python: `3.11.9` (호환 범위: `3.10 ~ 3.13`)
  - OS: macOS (darwin arm64) 및 Linux (Ubuntu 22.04 LTS x86_64)
- **핵심 라이브러리 스펙**:
  - 전송 엔진: `httpx >= 0.28.1` (동기 `Client` 및 비동기 `AsyncClient` 듀얼 풀)
  - 스키마 검증: `pydantic >= 2.10.6`
  - 설정 파싱: `pyyaml >= 6.0.2`
- **테스트 격리 및 결정론(Determinism) 확보 방안**:
  - 외부 실제 네트워크 I/O는 `respx 0.23.1`을 사용하여 100% 인메모리로 격리 모킹합니다. 네트워크 환경에 따른 테스트 불안정성(Flakiness)을 제거하고 수백 밀리초 단위의 빠른 피드백 루프를 유지합니다.
  - 지수 백오프 테스트 시 실제 대기 시간(`time.sleep`, `asyncio.sleep`)은 `monkeypatch`로 가로채어 테스트 실행 지연을 방지하되, 계산된 대기 시간 값의 수학적 상한/하한은 엄격히 대조합니다.
  - 계층형 설정 테스트는 `tmp_path` 기반 임시 파일과 프로세스 격리 환경변수로 기존 개발 장비의 설정을 오염시키지 않습니다.

---

## 3. 장애 시나리오 중심 테스트 매트릭스 (Test Matrix)

| 케이스 ID | 검증 도메인 | 장애 및 엣지 시나리오 | 사전 조건 및 입력 데이터 | 기대 결과 및 패스 기준 (Pass Criteria) |
| :--- | :---: | :--- | :--- | :--- |
| **`TC-RETY-001`** | 재시도 분산 | 503 수신 시 Full Jitter 대기 및 복구 | 1차 시도 503 반환, 2차 시도 200 반환 모킹 | - 2회 호출 후 성공 반환<br>- 재시도 대기 시간 $T_{wait}$이 $0 \le T \le \min(30, 0.5 \times 2^k)$ 범위 내 균등 난수로 계산되는지 확인 |
| `TC-RETY-002` | Thundering Herd | 서버의 `Retry-After` 헤더 파싱 및 상한선 초과 방어 | `429 Too Many Requests`<br>Case 1: `Retry-After: 5`<br>Case 2: `Retry-After: 60` | - Case 1: 최소 5초 대기 적용 후 재시도<br>- Case 2: 최대 상한(30초)을 초과하므로 스레드 점유를 막기 위해 즉시 재시도 중단 및 429 반환 |
| `TC-RETY-003` | 보안 Fail-Fast | SSL 핸드셰이크 실패 시 불필요한 재시도 차단 | `ssl.SSLError` ("Certificate verification failed") 모의 주입 | 인증서 만료나 도메인 불일치는 재시도로 해결되지 않으므로, 1회 시도 즉시 중단(Fail-Fast)하고 예외를 반환 |
| `TC-RETY-004` | 멱등성 보호 | 비멱등 메서드(POST, PATCH)의 재시도 기본 차단 | `POST /orders` 요청 중 503 에러 발생 | - `retry_on_post=False`(기본값): 중복 주문 방지를 위해 1회 시도 후 즉시 503 반환<br>- `retry_on_post=True` 명시 시에만 재시도 수행 |
| **`TC-CONC-001`** | 커넥션 풀 경합 | 50개 스레드가 커넥션 풀(크기 15)을 동시 경합 | `ThreadPoolExecutor(max_workers=15)`, 50개 동시 GET 호출 | 풀 고갈로 인한 요청 누락이나 Deadlock 없이, 풀 큐를 통해 50건 전수 200 OK 완료 |
| `TC-CONC-002` | 동시성 회복 | 20개 비동기 요청이 동시에 503을 만나는 재시도 폭풍 | `asyncio.gather`로 20개 코루틴 동시 호출, 첫 시도 503 주입 | Full Jitter가 각 코루틴의 재시도 시점을 분산시켜 대상 서버 2차 충격 없이 20건 전수 정상 복구 |
| `TC-CONC-003` | 리소스 회수 | 세션 종료 및 비정상 종료 시 소켓 누수 제로 | 동기/비동기 호출 수행 후 `close()`, `aclose()` 호출 | - `_sync_client`, `_async_client` 풀 인스턴스 `None` 정리 확인<br>- 프로세스 종료 훅(`atexit.register(http.close_all)`) 등록 검증 |
| **`TC-ENG-001`** | 메모리 안전망 | 1MB 초과 대용량 악성/오류 페이로드 유입 방어 | 원격 서버가 1MB + 500바이트 크기의 텍스트 스트림 응답 | 메모리에 전체를 적재하지 않고 1,048,576바이트에서 절삭 후 `[TRUNCATED: Response body exceeded 1MB]` 표기 부착 |
| `TC-ENG-002` | 이벤트 루프 | 백그라운드 작업 중 이벤트 루프가 닫히거나 교체된 경우 | `AsyncClient` 생성 후 강제로 `loop.close()` 및 새 루프 진입 | `RuntimeError: Event loop is closed` 에러를 방지하고 새 활성 루프에 바인딩된 클라이언트를 투명하게 재생성 |
| **`TC-RESP-001`** | Result / DTO | 200 OK 응답 수신 시 DTO 파싱 및 민감정보 보호 | 정상 응답 데이터 수신, `Authorization: Bearer secret-token` 포함 | - `res.is_success == True`<br>- `res.into(UserDto)` 호출 시 타입 안전 객체 반환<br>- 로그 출력용 `safe_headers` 조회 시 토큰 마스킹(`***`) 적용 |
| `TC-RESP-002` | 스키마 드리프트 | API 명세와 서버 실제 응답 필드 불일치 | Pydantic 필수 필드(`name`)가 누락된 200 OK 본문 수신 | 크래시 없이 `DtoValidationError`를 발생시키며, 디버깅을 위해 응답 본문 요약본을 에러 메시지에 포함 |
| `TC-RESP-003` | 예외 흐름 제어 | 404/500 에러 응답 수신 시 명시적 처리 경로 | 404 Not Found 수신 상태 | - `res.unwrap()` 호출 시 상세 원인을 담은 `ApiCallError` 예외 방출<br>- `res.unwrap_or(default_obj)` 호출 시 안전하게 기본값 반환 |
| **`TC-CONF-001`** | 계층형 설정 | 다중 소스(ENV > YAML > JSON > Defaults) 설정 충돌 | 동일 키(`timeout`)가 YAML(8.0), ENV(12.0), kwargs(20.0)에 존재 | 우선순위(`kwargs > ENV > YAML > JSON > Defaults`)에 따라 20.0이 최종 채택되고 누락된 값만 상속 |
| `TC-CONF-002` | 잘못된 설정 | 잘못된 URL 스키마 및 음수 타임아웃 주입 | `base_url="ftp://domain"`, `timeout=-5.0` 주입 | 클라이언트 생성 시점에 `ConfigurationValidationError`를 발생시켜 런타임 통신 장애 사전 차단 |
| **`TC-DEC-001`** | 선언적 라우팅 | 데코레이터 URL 템플릿 파라미터 누락 | `@get("/users/{user_id}/{sub_id}")` 정의 후 `user_id`만 전달 | 불완전한 URL로 잘못된 요청이 나가지 않도록 호출 즉시 `ValueError("sub_id")` 발생 |

---

## 4. 합격 기준 및 출시 조건 (Exit Criteria)

1. **테스트 통과율 100%**: 작성된 72개 단위/통합/부하 테스트 케이스 전수 무결점 통과 (0 Failure, 0 Error).
2. **코드 커버리지 95% 이상**: 패키지 전체 라인 커버리지 95% 이상을 달성하되, 미수행 5%는 방어적 fallback 구문임을 소명할 것.
3. **결함 허용 기준**: 운영 배포를 막는 Blocker 및 Critical 결함 0건.
4. **리소스 안전성 검증**:
   - `yaml.safe_load` 사용으로 임의 객체 실행 취약점 방어.
   - 1MB 응답 절삭 기능 정상 작동 확인.
   - 고동시성 50 스레드 / 100 코루틴 상황에서 커넥션 누수 0건 입증.
