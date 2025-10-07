# backend/Dockerfile - Corrected and Optimized

FROM python:3.11-slim

# Set core environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# CRITICAL FIX: Add the application directory to the Python search path
ENV PYTHONPATH=/app 

# Create app directory
ENV APP_HOME=/app
WORKDIR $APP_HOME

# Install OS build dependencies (required for psycopg2-binary, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    # Also add libpq-dev which is often needed for psycopg2 compilation on Alpine/Slim images
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt FIRST to optimize layer caching
COPY requirements.txt ./

# CRITICAL FIX: Install dependencies in a single, robust layer. 
# This command *must* execute correctly, installing all required packages.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source (main.py, routers/, etc.)
COPY . .

# Expose port used by uvicorn
EXPOSE 8000

# Use a simple, explicit uvicorn command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]