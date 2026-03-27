FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and install from lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY . .

# Create shared directory for SQLite database
RUN mkdir -p /app/shared

# Set environment variables
ENV PYTHONPATH=/app/app
ENV DATABASE_URL=sqlite:////app/shared/rent_scraper.db

# Expose port
EXPOSE 8000

# Start the application
CMD ["sh", "-c", "mkdir -p /app/shared && touch /app/shared/rent_scraper.db && cd app && uv run uvicorn app:app --host 0.0.0.0 --port 8000"]