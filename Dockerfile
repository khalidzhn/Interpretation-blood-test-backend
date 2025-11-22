FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY panel/ panel/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=${PORT:-8080}

EXPOSE ${PORT}

CMD uvicorn app.app_server:app --host 0.0.0.0 --port ${PORT}
