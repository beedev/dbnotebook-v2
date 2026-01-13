"""
Gunicorn configuration for DBNotebook production deployment.

Optimized for concurrent request handling with gevent workers.
Based on 14 CPU cores and 24GB RAM infrastructure.
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:7860"
backlog = 2048

# Worker processes
# For I/O-bound tasks (LLM calls, database queries), gevent is ideal
# Using 4 workers with gevent - each can handle many concurrent connections
workers = int(os.getenv("GUNICORN_WORKERS", 4))
worker_class = "gevent"

# Gevent worker connections
# Each gevent worker can handle many concurrent connections via greenlets
worker_connections = 1000

# Timeout for worker response (LLM calls can take 30+ seconds)
timeout = 180  # 3 minutes - accounts for slow LLM responses
graceful_timeout = 60

# Keep-alive connections
keepalive = 5

# Process naming
proc_name = "dbnotebook"

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (optional, configure if needed)
# keyfile = None
# certfile = None

# Pre-fork hook - runs before worker processes are forked
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    # Gevent monkey patching is handled in wsgi.py before any imports
    pass

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass

def worker_exit(server, worker):
    """Called just after a worker has been exited, in the master process."""
    pass

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    pass

def on_exit(server):
    """Called just before exiting Gunicorn."""
    pass

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100  # Add randomness to prevent all workers restarting at once
