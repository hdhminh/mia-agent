FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install --global opencode-ai

RUN pip install --no-cache-dir \
    "fastapi>=0.115,<1" \
    "httpx>=0.27,<1" \
    "uvicorn[standard]>=0.30,<1" \
    "pydantic>=2,<3"

COPY infra/opencode-gateway/service /app/service

EXPOSE 8015

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8015"]
