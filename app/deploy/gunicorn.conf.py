"""Gunicorn settings for a Linux server (run: gunicorn -c deploy/gunicorn.conf.py wsgi:app).

Gunicorn does not run on Windows; there use `python -m waitress --port 8000 wsgi:app`.
Set APP_CONFIG=prod and SECRET_KEY in the environment first.
"""

bind = "127.0.0.1:8000"  # the reverse proxy (nginx) forwards to this address
workers = 2  # SQLite allows many readers and one writer at a time; more workers rarely help
threads = 8  # the live order page keeps one long request open per visitor
worker_class = "gthread"
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
