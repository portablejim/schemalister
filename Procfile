web: gunicorn schemalister.wsgi:application

worker: celery -A schemalister worker --loglevel=info

release: django-admin migrate --no-input && django-admin collectstatic --no-input
