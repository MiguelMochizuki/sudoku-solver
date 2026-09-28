FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends swi-prolog build-essential pkg-config \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser
USER appuser

EXPOSE 8501

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8501"]