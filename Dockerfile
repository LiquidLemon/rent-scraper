FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --system .

# Copy application code
COPY . .

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app/app
ENV DATABASE_URL=sqlite:////app/rent_scraper.db

# Expose port
EXPOSE 8000

# Start the application
CMD ["sh", "-c", "cd /app && touch rent_scraper.db && cd app && uvicorn app:app --host 0.0.0.0 --port 8000"]