FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.in requirements.lock pyproject.toml README.md /app/

RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . /app

EXPOSE 8501

CMD ["python", "main.py", "config/paper.yaml"]
