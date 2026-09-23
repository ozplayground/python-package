# ozplayground / python-package

> 백엔드 애플리케이션 개발에 필요한 공통 파이썬 패키지 모노레포

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

프로덕션 서비스 구축 시 반복되는 데이터베이스 연결, 외부 HTTP 통신, 유틸리티 로직을 모듈화하여 패키지 형태로 제공합니다.  
모든 패키지는 독립된 가상환경과 빌드 설정을 가지며, 정적 타입 검사와 테스트 커버리지를 통과한 산출물만 관리합니다.

---

## 패키지 목록 (Packages)

| 패키지명 | 버전 | 주요 기능 및 기반 기술 | 디렉토리 | 엔지니어링 문서 |
| :--- | :---: | :--- | :---: | :---: |
| [`sqla-autoconfig`](./sqla-autoconfig) | `v0.1.0` | 환경변수/YAML 설정 기반 데이터베이스 엔진 자동 구성 및 커넥션 풀 제어 (SQLAlchemy 2.0) | [코드 및 가이드](./sqla-autoconfig/README.md) | [명세서](./docs/sqla-autoconfig/) |
| [`courier`](./courier) | `v0.1.0` | 지수 백오프/Full Jitter 재시도 및 표준 응답 래퍼를 제공하는 HTTP 클라이언트 (HTTPX & Pydantic v2) | [코드 및 가이드](./courier/README.md) | [명세서](./docs/courier/) |
| [`quiver`](./quiver) | `v0.1.0` | 런타임 의존성 0개의 순수 파이썬 유틸리티 툴킷 (불변 컬렉션, 함수 합성, 단조 시계 계측) | [코드 및 가이드](./quiver/README.md) | [명세서](./docs/quiver/) |

> 각 패키지의 설치 방법, 설정 예제 및 상세 API는 개별 패키지 디렉토리의 `README.md`를 참고하시기 바랍니다.

---

## 엔지니어링 산출물 (`docs/`)

기획, 아키텍처 의사결정(ADR), 구현 및 리뷰, QA 및 배포 검증서는 각 패키지 디렉토리 하위 `docs/`에 분리 보관됩니다:

- [sqla-autoconfig 엔지니어링 문서](./docs/sqla-autoconfig/)
- [courier 엔지니어링 문서](./docs/courier/)
- [quiver 엔지니어링 문서](./docs/quiver/)

---

## 라이선스 (License)

이 리포지토리는 [MIT License](./LICENSE)에 따라 배포됩니다.
