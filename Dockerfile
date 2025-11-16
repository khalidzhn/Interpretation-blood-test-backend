FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY panel/ panel/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EB provides PORT, default to 8080
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.app_server:app --host 0.0.0.0 --port $PORT"]
