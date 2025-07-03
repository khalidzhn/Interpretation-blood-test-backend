FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy requirements (create requirements.txt if you don't have one)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Start the app with Uvicorn
CMD ["uvicorn", "app.app_server:app", "--host", "0.0.0.0", "--port", "8000"]