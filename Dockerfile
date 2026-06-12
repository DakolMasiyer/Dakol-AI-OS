FROM python:3.11-slim

RUN apt-get update && apt-get install -y libsndfile1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-prod.txt requirements-base.txt requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
