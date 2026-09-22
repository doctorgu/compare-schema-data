# compare-schema-data

[English](README.md) | [한국어](README_KO.md)

`compare-schema-data`는 데이터베이스 환경(dev, stg, prd 등) 간의 MySQL 스키마(테이블, 컬럼, 인덱스, 외래키, 뷰) 및 참조 테이블 데이터의 차이점을 비교하고, 버전별 변경 이력을 추적하여 **Markdown** 및 **Excel** 리포트로 생성해 주는 도구입니다.

크게 두 가지 비교 기능을 제공합니다:
1. **환경 간 비교 (`compare`)**: 동일 버전 시점에서 서로 다른 환경(예: `dev` vs `stg`, `stg` vs `prd`) 간 스키마 및 데이터의 불일치 항목 비교.
2. **버전별 이력 로깅 (`log`)**: 동일 환경 내에서 버전 간 스냅샷(예: `이전 버전(prev_version)` vs `현재 버전(version)`)을 비교하여 추가(added), 삭제(removed), 변경(changed)된 내역 추적.

---

## 주요 특징

- **포괄적인 스키마 검증**:
  - **테이블 & 뷰**: 테이블 유형(`BASE TABLE`, `VIEW`), 테이블 주석(Comment) 비교.
  - **컬럼(Columns)**: 데이터 타입, 상세 타입(길이/정밀도/소수점 포함), Null 허용 여부, 기본값(Default), 코멘트, 순서(Position) 비교.
  - **인덱스(Indices)**: 복합 인덱스 컬럼 순서, 인덱스 유형(BTREE 등), 고유 여부(`IS_UNIQUE`) 비교 (외래키 생성 자동 인덱스는 지능적으로 제외하여 실제 인덱스만 비교).
  - **외래키 제약조건(Foreign Keys)**: 제약조건명, 대상 컬럼, 참조 테이블 및 참조 컬럼 비교.
- **선택적 테이블 데이터 비교**:
  - 메뉴, 공통코드, 상태값 등 환경 간 일치해야 하거나 버전별 변경 관리가 필요한 주요 참조/마스터 테이블 데이터 비교.
  - SQLite 내에 `STRICT` 모드 테이블을 자동 생성하고, MySQL 데이터 타입을 SQLite strict 타입으로 자동 변환.
  - 컬럼 구조 변경 감지 시 SQLite 기존 테이블을 백업(`_back_<타임스탬프>_<테이블명>`)하고 최신 구조로 자동 재생성.
  - 기본키/복합키(`key_columns`)를 기준으로 누락된 행(`data_not_exists`, `data_added`, `data_removed`) 및 컬럼 단위 값 불일치(`data_diff`, `data_changed`) 검출.
- **2단계 SQLite 로컬 스냅샷 아키텍처**:
  - MySQL `INFORMATION_SCHEMA`로부터 메타데이터와 대상 데이터를 추출하여 로컬 SQLite(`schema_data.sqlite3`)에 캐싱.
  - 실제 데이터베이스 비교 시 라이브 운영 DB에 락(Lock)이나 부하를 주지 않고 로컬 SQLite에서 초고속 차이 분석 쿼리 수행.
- **환경별 제외 설정(Exclusion Filters)**:
  - 마이그레이션 관리 테이블(예: `alembic_version`)이나 특정 환경 전용 컬럼을 환경 간 비교 대상에서 제외 가능 (버전 간 변경 이력 로그에는 온전히 보존).
- **다양한 리포트 출력 포맷**:
  - **Markdown (`.md`)**: GitHub 마크다운 테이블 형태로 `<버전>_compare.md`와 `<버전>_log.md`로 분리 생성.
  - **Excel (`.xlsx`)**: 차이가 존재하는 카테고리별로 워크시트가 나뉘고 헤더 서식이 적용된 `<버전>_compare_log.xlsx` 생성.
- **안전한 환경변수 연동**:
  - YAML 설정 파일에서 `env.<변수명>`(예: `env.DB_USERNAME`, `env.DB_PASSWORD`) 문법을 지원하여 `.env` 파일 또는 시스템 환경변수로 안전하게 인증정보 관리.

---

## 시스템 구조 및 동작 원리

```text
+-------------------+      +-------------------+      +-------------------+
|     dev MySQL     |      |     stg MySQL     |      |     prd MySQL     |
+---------+---------+      +---------+---------+      +---------+---------+
          |                          |                          |
          +--------------------------+--------------------------+
                                     |
                               [ 1. import ]
                                     |
                                     v
                       +---------------------------+
                       |   schema_data.sqlite3     |
                       | (스키마 및 데이터 스냅샷 저장)   |
                       +-------------+-------------+
                                     |
                              [ 2. compare ]
                                     |
                                     v
                   +-----------------+-----------------+
                   |                                   |
              (환경 간 비교)                       (버전별 변경 이력)
        a != b (예: dev vs stg)               a == b (dev vs dev)
                   |                                   |
                   v                                   v
          *_compare.md / .xlsx                 *_log.md / .xlsx
      (schema_not_exists, diff 등)         (schema_added, changed 등)
```

1. **`import` 단계**: 설정된 MySQL 인스턴스들의 `INFORMATION_SCHEMA.TABLES`, `COLUMNS`, `STATISTICS`, `KEY_COLUMN_USAGE` 및 지정된 `data_tables`를 조회하여 SQLite의 스키마 메타 테이블과 데이터 테이블에 `version`, `env_name`, `db_name` 태그와 함께 저장합니다.
2. **`compare` 단계**: 로컬 SQLite에서 최적화된 SQL 쿼리를 실행하여 차이점을 검출합니다.
   - `a != b` 항목(예: `dev.lms` vs `stg.lms`): **환경 간 비교 리포트**(`*_compare.md`) 생성.
   - `a == b` 항목(예: `dev.lms` vs `dev.lms`): 현재 `version`과 `prev_version` 간의 **버전 이력 로그**(`*_log.md`) 생성.

---

## 사전 요구사항

- Python >= 3.13
- MySQL 5.7+ 또는 8.0+
- [uv](https://github.com/astral-sh/uv) (권장) 또는 `pip`

---

## 설치 방법

### `uv` 사용 (권장)

```bash
# 리포지토리 클론
git clone https://github.com/doctorgu/compare-schema-data.git
cd compare-schema-data

# 가상환경 생성 및 활성화
uv venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 의존성 패키지 설치 (개발 모드)
uv pip install -e . --native-tls
```

### 일반 `pip` 사용

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

---

## 설정 가이드

설정은 YAML 파일(예: `config/config.yaml`)과 데이터베이스 인증용 `.env` 파일을 통해 이루어집니다.

### 1. `.env` 파일 설정

프로젝트 루트에 `.env` 파일을 생성합니다 (`.env.example` 참조):

```env
DB_USERNAME=데이터베이스_사용자명
DB_PASSWORD=데이터베이스_비밀번호
```

### 2. `config.yaml` 상세 구성

```yaml
# 리포트 출력 포맷: Markdown은 "md", Excel은 "xlsx"
output_type: md
# 리포트가 저장될 디렉터리 경로
output_dir: ./data
# 스키마 및 데이터 스냅샷이 저장될 SQLite 파일 경로
sqlite_path: ./db_client/schema_data.sqlite3

# 데이터 비교 대상 테이블 및 컬럼 정의
data_tables:
  - table: menu
    columns:
      - menu_code
      - upper_menu_code
      - menu_name
      - menu_url
      - is_delete
      - "order"
    key_columns:
      - menu_code
  - table: common_code
    columns:
      - group_code
      - code
      - code_name
      - code_description
      - "order"
      - is_use
    key_columns:
      - group_code
      - code

# 환경 간 비교 시 제외할 테이블 및 컬럼 목록
exclude_tables: ["alembic_version"]
exclude_columns: []

# 기본 DB 접속 정보 (env.<변수명> 문법으로 .env 연동 가능)
db_host: 127.0.0.1
db_port: 3306
db_username: env.DB_USERNAME
db_password: env.DB_PASSWORD

# 환경별 접속 설정 (생략된 항목은 상위 기본 설정을 상속받음)
envs:
  - name: dev
    db_names: [lms, lms_next]
    db_port: 4001
  - name: stg
    db_names: [lms]
    db_port: 4004
  - name: prd
    db_names: [lms]
    db_port: 4002

# 비교 대상 목록
compare_list:
  # 서로 다른 환경 간 비교 (*_compare 리포트 생성)
  - a: dev.lms
    b: dev.lms_next
  - a: dev.lms
    b: stg.lms
  - a: stg.lms
    b: prd.lms

  # 동일 환경 자기 자신 비교 (버전 간 변경 이력 *_log 리포트 생성)
  - a: dev.lms
    b: dev.lms
  - a: stg.lms
    b: stg.lms
  - a: prd.lms
    b: prd.lms
```

---

## 실행 방법

### 1단계: 스키마 및 데이터 가져오기 (`import`)

설정 파일에 정의된 모든 환경의 MySQL DB에 접속하여 스키마 정보와 테이블 데이터를 SQLite로 추출합니다.

```bash
# 기본 실행 (버전 미지정 시 현재 시각 타임스탬프 자동 부여: YYYYMMDDHH00)
import --config_path config/config.yaml

# 특정 버전명을 직접 지정하여 실행
import --config_path config/config.yaml --version 202609221530
```

Python 코드(`.py`)에서 직접 호출할 수도 있습니다:

```python
from compare_schema_data.import_ import import_schema_data

import_schema_data(config_path="config/config.yaml")
# 특정 버전명을 직접 지정할 경우:
# import_schema_data(config_path="config/config.yaml", version="202609221530")
```

### 2단계: 스키마 및 데이터 비교 (`compare`)

SQLite에 저장된 스냅샷을 기반으로 비교를 수행하고 지정된 `output_dir`에 결과 파일을 생성합니다.

```bash
# 최신 버전과 그 직전 버전을 자동으로 감지하여 비교
compare --config_path config/config.yaml

# 특정 버전과 이전 버전을 직접 지정하여 비교
compare --config_path config/config.yaml --version 202609221530 --prev_version 202609211600
```

Python 코드(`.py`)에서 직접 호출할 수도 있습니다:

```python
from compare_schema_data.compare import compare_schema_data

compare_schema_data(config_path="config/config.yaml")
# 특정 버전을 직접 지정하여 비교할 경우:
# compare_schema_data(config_path="config/config.yaml", version="202609221530", prev_version="202609211600")
```

---

## 결과 리포트 종류 및 구조

설정된 `output_type`에 따라 다음과 같은 리포트가 생성됩니다:

### 1. Markdown 리포트 (`output_type: md`)

차이점이 발견된 경우 `output_dir`에 두 개의 파일이 분리되어 저장됩니다:

#### A. 환경 간 비교 리포트 (`<버전>_compare.md`)
동일 버전 시점에서 서로 다른 환경 간의 차이점을 요약합니다:
- `## schema_not_exists`: 한쪽 환경에만 존재하고 다른 환경에는 누락된 객체 (테이블, 뷰, 컬럼, 인덱스, 외래키).
- `## schema_diff`: 양쪽 환경 모두 존재하지만 속성이 다른 항목 (컬럼 기본값, Null 허용 여부, 코멘트, 데이터 타입/길이 등).
- `## data_not_exists`: 기본키 기준 한쪽에만 존재하는 행 데이터.
- `## data_diff`: 동일 키를 가진 행에서 특정 컬럼의 값이 다른 항목.

*`schema_diff` 출력 예시:*

| table_name | column_name | index_name | constraint_name | different_type | value_a | value_b | env_db_a | env_db_b |
|---|---|---|---|---|---|---|---|---|
| order | is_user_dismissed | | | is_nullable | NO | YES | dev.lms | dev.lms_next |
| textbook_classification | classification_en | | | is_nullable | YES | NO | dev.lms | dev.lms_next |

#### B. 버전 변경 이력 리포트 (`<버전>_log.md`)
동일 환경에서 이전 버전(`prev_version`)과 현재 버전(`version`) 사이의 변경 내역을 기록합니다:
- `## schema_added`: 신규 추가된 테이블, 컬럼, 인덱스, 제약조건.
- `## schema_removed`: 삭제된 테이블, 컬럼, 인덱스, 제약조건.
- `## schema_changed`: 컬럼 타입, 기본값, 코멘트 등 변경된 속성.
- `## data_added`: 신규 추가된 데이터 행.
- `## data_removed`: 삭제된 데이터 행.
- `## data_changed`: 값이 수정된 데이터 컬럼.

*`schema_added` 출력 예시:*

| table_name | column_name | index_name | constraint_name | object_type | env_db | version | version_old |
|---|---|---|---|---|---|---|---|
| leveltest_product_policy | | | | table | dev.lms | 202609221530 | 202609211600 |
| leveltest_product_policy | policy_code varchar(20) NOT NULL COMMENT '정책코드' | | | column | dev.lms | 202609221530 | 202609211600 |

### 2. Excel 리포트 (`output_type: xlsx`)

차이가 존재하는 각 카테고리별로 시트가 자동 분리되고, 헤더에 볼드 스타일이 적용된 통합 엑셀 파일 `<버전>_compare_log.xlsx`가 생성됩니다.

---

## 프로젝트 디렉터리 구조

```text
compare-schema-data/
├── .env.example                     # 환경변수 템플릿 파일
├── pyproject.toml                   # 패키지 메타데이터, 의존성, CLI 스크립트 등록
├── README.md                        # 영문 문서
├── README_KO.md                     # 국문 문서
├── config/
│   ├── config.yaml                  # 전체 스키마 및 데이터 비교 설정 파일
│   └── config_data.yaml             # 데이터 비교 중심 예제 설정 파일
├── data/                            # 생성된 결과 리포트 (*_compare.md, *_log.md, *.xlsx)
├── db_client/
│   ├── schema.sql                   # 메타데이터 저장을 위한 SQLite DDL
│   ├── schema_settings.py           # SQLite 클라이언트 커넥션 풀 및 쿼리 로거 설정
│   ├── schema_client.py             # SQLite 클라이언트 클래스
│   ├── schema_data.sqlite3          # SQLite 스냅샷 데이터베이스 파일
│   └── queries/
│       ├── schema/                  # SQLite 차이점 분석 쿼리 모음
│       │   ├── schema.yml
│       │   └── data.yml
│       └── source/                  # MySQL 메타데이터/데이터 추출 쿼리 모음
│           ├── import_schema.yml
│           └── import_data.yml
└── compare_schema_data/
    ├── import_.py                   # MySQL 추출, SQLite 적재 로직 및 import_by_args CLI
    ├── compare.py                   # 스키마 및 데이터 차이 분석 엔진 및 compare_by_args CLI
    ├── config.py                    # Pydantic 설정 모델 및 환경변수 처리 로직
    ├── models.py                    # 데이터 모델, 비교 타입, 테이블 헤더 정의
    ├── excel_helper.py              # XlsxWriter 기반 엑셀 리포트 작성기
    ├── markdown_helper.py           # tabulate 기반 마크다운 리포트 작성기
    ├── util_mysql.py                # MySQL 타입 변환 및 DDL 생성 유틸리티
    └── util_path.py                 # 파일 경로 및 YAML 로딩 유틸리티
```

---

## 코드 스타일 및 린트 검사

프로젝트는 [ruff](https://github.com/astral-sh/ruff)를 통해 코드 스타일과 포맷팅을 관리합니다:

```bash
# 린트 검사
ruff check .

# 코드 자동 포맷팅
ruff format .
```

---

## 라이선스

이 프로젝트는 [MIT License](LICENSE)에 따라 자유롭게 사용 및 수정할 수 있습니다.

## 작성자

- **Gu Park** - [doctorgu@kakao.com](mailto:doctorgu@kakao.com) - [GitHub](https://github.com/doctorgu)
