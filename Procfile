web: gunicorn schemalister.wsgi:application

release: django-admin migrate --no-input && django-admin collectstatic --no-input
