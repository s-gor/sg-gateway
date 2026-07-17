FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir flask waitress

COPY app ./app
COPY engines ./engines

EXPOSE 8080

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "app.main:app"]
