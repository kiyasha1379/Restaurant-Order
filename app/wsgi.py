"""Entry point for `flask run` and for production servers such as Gunicorn."""

from restaurant import create_app

app = create_app()
