FROM python:3.12-slim AS builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends swi-prolog build-essential pkg-config \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends swi-prolog \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

RUN useradd -m appuser
USER appuser

EXPOSE 8501

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8501"]
