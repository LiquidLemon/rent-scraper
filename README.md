# Rent Scraper

A web-based rental listing scraper with automated notifications.

## Quick Start

### Docker (Recommended)

1. **Development:**
   ```bash
   docker-compose up -d
   ```

2. **Production (using pre-built image):**
   ```bash
   export GITHUB_REPOSITORY=your-username/rent-scraper
   export SECRET_KEY=your-secure-secret-key
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Create admin user:**
   ```bash
   docker-compose exec web python /app/create_user.py admin your-password
   ```

The web interface will be available at http://localhost:8000

### Local Development

```bash
uv run python app/app.py
```

## Deployment

The project includes GitHub Actions that automatically build and push Docker images to GitHub Container Registry (GHCR) on every push to master/main branch.

## Features

- Web-based query management with testing
- Discord webhook notifications
- Automated scraping with status tracking
- User authentication and isolation
- Timezone-aware relative timestamps
- Docker containerization for easy deployment