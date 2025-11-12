# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# Application configuration defaults (override via platform env)
ENV COZE_API_TOKEN=""
ENV WORKFLOW_ID="756987740896"
ENV SCHEDULE_TIME="21:00"
ENV TIMEZONE="Asia/Shanghai"
ENV INITIAL_RETRY_DELAY="5"
ENV MAX_BACKOFF="300"
ENV COZE_API_BASE_URL=""
ENV COZE_REGION=""
ENV LOG_LEVEL="INFO"
ENV JITTER_MAX_SECONDS="3"
ENV SLEEP_CHUNK_SECONDS="5"
ENV STOP_ON_SHUTDOWN="true"

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY wewerss.py ./wewerss.py

CMD ["python", "wewerss.py"]