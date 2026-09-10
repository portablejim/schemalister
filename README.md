# Schema Lister

Django application for listing and exporting all objects and fields within a Salesforce Org. This app is designed to run on Heroku, or Dokku, but could be amended to run locally or any desired server

## Setup

To set this up on your own Heroku account, this app does require some knowledge of deploying Django apps. The following Heroku resources are required:
- Heroku Postgres (or alternative database)
- Redis To Go (or Heroku Redis - but might require some minor changes)

To set this up on Dokku, this needs a PosgreSQL and Redis (or compatible) server.

Required Environment Variables:

| Name | Description |
| -- | -- |
| DJANGO_SECRET_KEY | Random Key for Django. App will exit if not provided, however a new key will be generated in the logs, which can be used.
| REDIS_URL | The connection string for Redis. Without this login and scheduling won't work.
| SALESFORCE_CONSUMER_KEY | OAuth detail. Get from Salesforce External Client App configuration => 'Consumer Key'.
| SALESFORCE_CONSUMER_SECRET |OAuth detail. Get from Salesforce External Client App configuration => 'Consumer Secret'. 
| SALESFORCE_REDIRECT_URI | OAuth detal. Path should be `/auth/callback`. (e.g. `http://localhost:8000/auth/callback`)
| SECRETS_ENCRYPTION_KEY | 32 byte key. App will exit if not provided, however a new key will be generated in the logs, which can be used.

If `ENVIRONMENT` is unset, or is set to `production`, a PostgreSQL connection is required. This is set either via a single `DATABASE_URL` connection string (e.g. `postgres://user:password@host:port/database`) or via separate `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST` AND `PGPORT` variables.
 a SQLite database is used instead of PostgreSQL. Otherwise
