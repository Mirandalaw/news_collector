FROM python:3.12-slim

# 로그가 버퍼링 없이 즉시 출력되도록 (크래시 시 로그 유실 방지)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# psycopg2-binary는 대부분 플랫폼에서 바이너리 wheel로 설치된다.
# wheel이 없을 때 소스 컴파일 폴백이 발생하므로 빌드툴을 준비하되,
# 설치 완료 후 동일 레이어에서 제거해 이미지 크기를 최소화한다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && pip install --no-cache-dir psycopg2-binary==2.9.11 \
    && apt-get purge -y --auto-remove gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 레이어 분리 — requirements.txt 변경 시에만 pip install 다시 실행
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY app/     app/
COPY scripts/ scripts/

# logs/, output/ 는 docker-compose.yml 볼륨 마운트로 처리
CMD ["python", "scripts/run_all.py", "--telegram", "--no-console"]
