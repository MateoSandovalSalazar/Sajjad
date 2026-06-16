FROM python:3.12-slim

# System deps: scanner tools + WeasyPrint libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    dnsutils \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install the sajjad scanning engine (root package)
# Build context is Sajjad/ root so these paths work
COPY pyproject.toml pyproject.toml
COPY sajjad/ sajjad/
RUN uv pip install --system --no-cache .

# Install backend dependencies
COPY backend/pyproject.toml backend/pyproject.toml
WORKDIR /app/backend
RUN uv pip install --system --no-cache \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
    pydantic pydantic-settings email-validator \
    python-jose[cryptography] bcrypt \
    celery[redis] redis httpx aiosmtplib jinja2 \
    python-dotenv slowapi dnspython psycopg2-binary \
    weasyprint structlog python-multipart

COPY backend/ .

ENV PATH="/go/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
