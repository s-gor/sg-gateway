FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY engines ./engines

RUN useradd --system --uid 10001 --create-home sg-gateway
USER sg-gateway

EXPOSE 8080

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "app.main:app"]