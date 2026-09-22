# [sqla-autoconfig] 패키지 배포 및 환경 검증 명세서 (Deployment Specification)

- **작성일자**: 2026-09-22
- **작성자**: 데브옵스 및 배포 엔지니어 (`devops-engineer`)
- **문서 버전**: v1.0
- **상태**: Approved

---

## 1. 패키지 빌드 및 배포 산출물 (Package Artifacts)

| 패키지 유형 | 파일명 | 형식 | 빌드 상태 |
| :--- | :--- | :---: | :---: |
| **Source Distribution (sdist)** | `sqla_autoconfig-0.1.0.tar.gz` | tar.gz | **BUILD SUCCESS** |
| **Pure Python Wheel** | `sqla_autoconfig-0.1.0-py3-none-any.whl` | Wheel | **BUILD SUCCESS** |

### 배포 파이프라인 (PyPI Publishing)
```bash
# 빌드 명령
uv build

# PyPI 배포 (API Token 인증)
uv publish --token $PYPI_API_TOKEN
```

---

## 2. 계층형 환경변수 및 설정 파일 규격서 (Environment & Config Specification)

### 2.1 우선순위 매트릭스
1. **명시적 전달 인자 (`kwargs`)**: 최우선 순위
2. **환경변수 (`DB_*` 또는 `SQLA_*`)**: 컨테이너 및 쿠버네티스 환경 권장
3. **YAML 파일 (`database.yaml`, `database.yml`, `config.yaml`, `application.yml`)**: 로컬 및 스테이징 권장
4. **JSON 파일 (`database.json`, `config.json`, `application.json`)**: 범용 마이크로서비스 설정 권장
5. **기본값 (Hardcoded Defaults)**: 안전한 고성능 기본값 자동 주입

### 2.2 `.env.example`
```ini
# Database Connection Settings
DB_TYPE=postgres            # postgres, mysql, mariadb, sqlite
DB_HOST=localhost
DB_PORT=5432
DB_USER=myuser
DB_PASSWORD=secret_password
DB_NAME=production_db

# Optional Full URL (Overrides host/port/user/password)
# DATABASE_URL=postgresql+asyncpg://myuser:secret@localhost:5432/production_db

# High-Concurrency Pool Tuning (Defaults are production-ready)
DB_POOL_SIZE=20             # 기본 상주 커넥션 수
DB_MAX_OVERFLOW=10          # 최대 버스트 허용 커넥션 수
DB_POOL_RECYCLE=1800        # 유휴 커넥션 재생성 주기 (초)
DB_POOL_PRE_PING=true       # 좀비 커넥션 자동 퇴출
DB_POOL_TIMEOUT=30.0        # 커넥션 체크아웃 타임아웃 (초)
DB_ECHO=false               # SQL 쿼리 로깅 여부
```

### 2.3 `database.yaml` 예시 (계층형)
```yaml
database:
  type: postgres
  connection:
    host: localhost
    port: 5432
    user: app_user
    password: app_password
    name: app_db
  pool:
    size: 20
    max_overflow: 10
    recycle: 1800
    pre_ping: true
    timeout: 30.0
  echo: false
```

### 2.4 `database.json` 예시 (계층형)
```json
{
  "database": {
    "type": "mysql",
    "connection": {
      "host": "127.0.0.1",
      "port": 3306,
      "user": "root",
      "password": "root_password",
      "name": "app_db"
    },
    "pool": {
      "size": 25,
      "max_overflow": 15,
      "recycle": 1800,
      "pre_ping": true,
      "timeout": 30.0
    },
    "echo": false
  }
}
```

---

## 3. 다중 데이터베이스 통합 테스트베드 (Docker Compose Testbed)

PostgreSQL, MySQL, MariaDB와의 라이브 통합 검증을 위한 `docker-compose.yml` 명세입니다.

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: test-postgres
    environment:
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpassword
      POSTGRES_DB: testdb
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d testdb"]
      interval: 5s
      timeout: 5s
      retries: 5

  mysql:
    image: mysql:8.0
    container_name: test-mysql
    environment:
      MYSQL_ROOT_PASSWORD: testpassword
      MYSQL_DATABASE: testdb
      MYSQL_USER: testuser
      MYSQL_PASSWORD: testpassword
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "testuser", "-ptestpassword"]
      interval: 5s
      timeout: 5s
      retries: 5

  mariadb:
    image: mariadb:10.11
    container_name: test-mariadb
    environment:
      MARIADB_ROOT_PASSWORD: testpassword
      MARIADB_DATABASE: testdb
      MARIADB_USER: testuser
      MARIADB_PASSWORD: testpassword
    ports:
      - "3307:3306"
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 5s
      timeout: 5s
      retries: 5
```

---

## 4. 무중단 및 헬스체크 운영 가이드 (Production Readiness)
1. **좀비 커넥션 자동 치유**: `pool_pre_ping=True`를 통해 AWS RDS 다중 AZ 장애 조치(Failover)나 네트워크 지터 발생 시 끊어진 커넥션을 감지하여 즉각 신규 커넥션으로 복구합니다.
2. **프로세스 종료 시 자원 회수**: `atexit` 훅과 `db.dispose()`를 통해 컨테이너 SIGTERM 수신 시 모든 활성 엔진 풀을 안전하게 닫아 데이터베이스 서버의 세션 고갈을 방지합니다.
