"""Default gunicorn config for the docker environment.

To override, mount a new gunicorn config at /data/gunicorn.conf.py in your
Docker container.
"""

# pylint: disable=invalid-name

# Enable to log every request
# accesslog = "-"
errorlog = "-"
preload_app = True
workers = 1
worker_class = "gevent"
