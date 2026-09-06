FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app TZ=Asia/Bangkok
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 postgresql-client tzdata && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x scripts/entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["scripts/entrypoint.sh"]
