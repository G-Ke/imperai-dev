# Base guidelines for producing code in this project

## General

- The app is written using [Django 5.1](https://www.djangoproject.com/) and [Django-Ninja](https://django-ninja.rest-framework.com/) frameworks.
- Async should be used whenever possible, but certain database actions could be synchronous.


### Django-Ninja

- The API is defined in the `api.py` file.
- The API routes are defined in the `api.py` file.
- The API responses are defined in the `api.py` file.
- The API schemas are defined in the `models.py` file.

### Django

- Django has some built in async functionality, but it can be tricky. [Django Async](https://docs.djangoproject.com/en/5.1/topics/async/)
- The settings are defined in the `settings.py` file.

### Database

- The database models are defined in the `models.py` file.
- The database is postgresql run on [TimescaleDB](https://www.timescale.com/). Docs can be found [here](https://docs.timescale.com/).
- The data base has pgvector extension for vector storage. Docs can be found [here](https://pgvector.org/).
- The migrations are defined in the `migrations` folders.


## AI / LLM

### Together

- The app uses [Together](https://together.xyz/) for LLM inference. Docs can be found [here](https://docs.together.xyz/).
- 
