# Rent Scraper Web UI Project

## Project Overview
Converting an existing command-line rent scraper tool into a web-based UI using FastAPI. The tool scrapes multiple housing listing sites and notifies users of new offers.

## Key Requirements & Decisions
- **Framework**: FastAPI with templated HTML (Jinja2)
- **Authentication**: Session-based (simple, no JWT)
- **Database**: SQLite with SQLAlchemy and Alembic migrations
- **Frontend**: HTMX for interactivity, minimalistic/simple CSS styling
- **User base**: Small (only a few users), no public sign-ups
- **Notifications**: Discord webhooks only for now

## Architecture
- FastAPI app with session middleware
- SQLAlchemy models: User, SearchQuery, NotificationSetting, Offer
- Alembic for database migrations
- Templates in `templates/` directory
- Static files in `static/` directory

## Working Sources
- Only `trojmiasto.pl` scraper currently works
- Other scrapers in `sources.py` are outdated and need manual fixing

## Development Approach
- Work iteratively and confirm results at each stage
- Preserve existing scraping logic where possible
- No need to preserve existing SQLite data during migration

## Features to Implement
1. Basic login system with account creation script
2. Search query management (CRUD + test functionality)
3. Discord webhook notification settings
4. Integration with existing scraper logic