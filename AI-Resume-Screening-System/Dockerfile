# ============================================================
#  TalentSync / HireAI — Production Dockerfile
#  Multi-worker WSGI container with minimal OCR runtime & non-root user.
# ============================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    FLASK_ENV=production \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Install minimal production runtime libraries: Tesseract OCR (runtime only, no compiler tools) and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy dependency manifest and install wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application source code and configuration
COPY app/ ./app/
COPY wsgi.py gunicorn.conf.py run.py ./

# Create persistent storage directories with proper ownership for non-root user
RUN mkdir -p uploads/resumes uploads/temp data && \
    chown -R appuser:appgroup ${APP_HOME}

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 5000

# Automated container healthcheck probing the /api/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Production WSGI server command
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
