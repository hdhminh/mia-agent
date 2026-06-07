FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir \
        --extra-index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
        paddlepaddle==3.2.2
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mia_core /app/mia_core
COPY sql /app/sql

EXPOSE 8000

CMD ["uvicorn", "mia_core.app:app", "--host", "0.0.0.0", "--port", "8000"]
