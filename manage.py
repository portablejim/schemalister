#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import logging
import os
import secrets
import sys

logger = logging.getLogger(__name__) 


def main():
    load_dotenv()
    
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schemalister.settings')
    try:
        from django.core.management import execute_from_command_line
        from django.core.management.utils import get_random_secret_key
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # If the environment is not production, do extra checks
    if 'ENVIRONMENT' not in os.environ or os.environ["ENVIRONMENT"] != 'production':
        missing_django_secret_key = 'DJANGO_SECRET_KEY' not in os.environ or os.environ['DJANGO_SECRET_KEY'] is None or len(os.environ['DJANGO_SECRET_KEY']) < 1
        missing_jwt_secret_key = 'JWT_SECRET_KEY' not in os.environ or os.environ['JWT_SECRET_KEY'] is None or len(os.environ['JWT_SECRET_KEY']) < 1
        missing_secrets_encryption_key = 'SECRETS_ENCRYPTION_KEY' not in os.environ or os.environ['SECRETS_ENCRYPTION_KEY'] is None or len(os.environ['SECRETS_ENCRYPTION_KEY']) < 1
        if missing_django_secret_key or missing_jwt_secret_key or missing_secrets_encryption_key:
            logging.critical('There seems to be environment variables missing. It is dangerous to go alone! Take this!')
            if missing_django_secret_key:
                logging.critical('DJANGO_SECRET_KEY missing | Example: ' + get_random_secret_key())
            if missing_jwt_secret_key:
                logging.critical('JWT_SECRET_KEY missing | Example: ' + secrets.token_hex(32).decode('utf-8'))
            if missing_secrets_encryption_key:
                logging.critical('SECRETS_ENCRYPTION_KEY missing | Example: ' + Fernet.generate_key().decode('utf-8'))
            exit(1)


    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
