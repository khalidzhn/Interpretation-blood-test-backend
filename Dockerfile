FROM python:3.11-slim

# Set work directory
WORKDIR /app

COPY requirements.txt .
COPY panel/ panel/

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EB injects PORT env variable (e.g., 5000)
ENV PORT=5000

# EXPOSE the EB port (not 8000)
EXPOSE 5000

CMD ["sh", "-c", "uvicorn app.app_server:app --host 0.0.0.0 --port $PORT"]
