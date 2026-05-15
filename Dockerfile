FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

COPY requirements.txt .
RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
        pip install --retries 10 --timeout 100 -r requirements.txt && break; \
        if [ "$attempt" = "5" ]; then exit 1; fi; \
        sleep 5; \
    done; \
    rm -rf /root/.cache/pip

COPY app ./app
COPY scripts ./scripts
COPY main.py .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}"]
