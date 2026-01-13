#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting DBNotebook with Gunicorn..."
# Using gunicorn with gevent workers for better concurrent request handling
# Configuration is loaded from gunicorn.conf.py
exec gunicorn -c gunicorn.conf.py 'dbnotebook.wsgi:app'
