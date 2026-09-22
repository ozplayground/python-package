# ozplayground / python-package

> **Production-Ready, High-Quality Python Packages by ozplayground**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

실무에서 유용하게 활용할 수 있는 파이썬 라이브러리와 유틸리티 패키지 모음 리포지토리입니다.  
모든 패키지는 철저한 TDD, 엔지니어링 하네스 파이프라인, 그리고 고성능/무장애 아키텍처 원칙을 준수하여 관리됩니다.

---

## 📦 패키지 목록 (Packages)

| 패키지명 | 버전 | 설명 | 패키지 링크 | 상세 문서 |
| :--- | :---: | :--- | :---: | :---: |
| [`sqla-autoconfig`](./sqla-autoconfig) | `v0.1.0` | 데이터베이스 자동 구성 및 고동시성 커넥션 풀 관리 라이브러리 (SQLAlchemy 2.0) | [README 바로가기](./sqla-autoconfig/README.md) | [Docs](./docs/sqla-autoconfig/) |
| [`courier`](./courier) | `v0.1.0` | 고신뢰성 외부 API 전령 및 통일된 응답(Result 패턴) 프레임워크 (HTTPX & Pydantic v2) | [README 바로가기](./courier/README.md) | [Docs](./docs/courier/) |

> 각 패키지의 설치 방법, 환경변수/YAML/JSON 설정 예제, 상세 사용법은 해당 패키지 디렉토리의 `README.md`를 참조해 주세요.

---

## 📂 엔지니어링 산출물 (`docs/`)

각 패키지별 기획, 아키텍처(ADR), TDD 로그, 코드 리뷰, QA 및 배포 명세서는 `docs/{패키지명}/` 하위에서 체계적으로 관리됩니다:

- [sqla-autoconfig 산출물 문서 바로가기](./docs/sqla-autoconfig/)
- [courier 산출물 문서 바로가기](./docs/courier/)

---

## 📄 라이선스 (License)

This repository is licensed under the [MIT License](./LICENSE).
