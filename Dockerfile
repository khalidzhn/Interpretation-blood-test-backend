FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pdf2image (poppler-utils) and pytesseract (tesseract-ocr)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY panel/ panel/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=80

EXPOSE 80

CMD uvicorn app.app_server:app --host 0.0.0.0 --port 80
