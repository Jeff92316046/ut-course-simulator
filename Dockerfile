FROM python:3.13.5-alpine3.22 AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY ./src /app
COPY ./alembic.ini /alembic.ini
COPY ./migrate /migrate
COPY ./pyproject.toml /pyproject.toml
COPY ./uv.lock /uv.lock
# Install the application dependencies.
WORKDIR /
RUN uv sync --frozen --no-cache

# Run the application.
CMD ["/.venv/bin/fastapi", "run", "app/main.py", "--port", "80", "--host", "0.0.0.0"]