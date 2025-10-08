# backend/Dockerfile - Final, Robust Version for Mac/Dependency Issues

FROM python:3.11-slim

# Set core environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# CRITICAL: Ensures local Python packages (like 'routers') are found
ENV PYTHONPATH=/app 

# Create app directory and set as working directory
ENV APP_HOME=/app
WORKDIR $APP_HOME

# --- OS Dependency Installation Layer ---
# Install OS build dependencies (required for psycopg2-binary and general compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Python Dependency Installation Layer ---
# Copy requirements.txt FIRST for efficient cache invalidation
COPY requirements.txt ./

# CRITICAL FIX: Install all requirements in one layer
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Application Code Layer ---
# Copy application source (main.py, routers/, etc.)
COPY . .

# Expose port used by uvicorn
EXPOSE 8000

# Use a simple, explicit uvicorn command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]