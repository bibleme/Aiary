# Dockerfile

# 1. Python 3.12 Slim 이미지를 기반으로 사용합니다.
FROM python:3.12-slim

# 2. 작업 디렉토리를 /app으로 설정합니다.
WORKDIR /app

# 3. 시스템 의존성 설치 (🚨 이 부분을 수정/확인합니다)
# python3-dev: Python C 확장을 위해 필수. libpq-dev: PostgreSQL 드라이버(psycopg2)를 위해 필수.
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 4. requirements.txt를 복사하고 설치합니다. (이후 코드는 그대로 유지)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 모든 소스 코드(.을 통해 현재 루트 폴더의 모든 내용)를 작업 디렉토리(/app)로 복사합니다.
COPY . .

# 6. Uvicorn 서버를 실행하는 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]