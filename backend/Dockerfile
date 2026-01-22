# 1. Use official Python runtime
FROM python:3.12-slim

# 2. Set work directory
WORKDIR /app

# 3. Install pip, dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy project files
COPY . .

# 5. Expose FastAPI port
EXPOSE 8000

# 6. Run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
