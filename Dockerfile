FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install system dependencies for MySQL and Postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Create the user and set permissions
RUN useradd -m appuser && chown -R appuser /app

# 3. Install requirements BEFORE copying the whole project (faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the project files
COPY --chown=appuser:appuser . .

# 5. Switch to the non-root user
USER appuser

# 6. Run collectstatic
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "task_management.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
