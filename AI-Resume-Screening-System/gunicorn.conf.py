# ============================================================
#  TalentSync — Production Gunicorn Configuration
# ============================================================

import os

# Server socket
bind = os.getenv("BIND", f"0.0.0.0:{os.getenv('PORT', '5000')}")

# Worker processes: conservative default for container environments
# Multiplication: 2 workers * 4 threads = 8 concurrent request handlers
workers = int(os.getenv("WEB_CONCURRENCY", os.getenv("GUNICORN_WORKERS", "2")))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = "gthread"

# Worker lifecycle & timeouts: 120s accommodates heavy OCR & document parsing
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Logging: stdout / stderr for container log aggregators
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(L)ss)'
