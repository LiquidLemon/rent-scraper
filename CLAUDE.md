# Rent Scraper Web UI Project

## Project Overview
Web-based rent scraper that monitors multiple Polish housing listing sites and notifies users of new offers via Discord webhooks. Built with FastAPI.

## Tech Stack
- **Framework**: FastAPI with Jinja2 templates
- **Authentication**: Session-based (simple, no JWT)
- **Database**: SQLite with SQLAlchemy and Alembic migrations
- **Frontend**: HTMX for interactivity, minimalistic CSS
- **Notifications**: Discord webhooks
- **Testing**: pytest with pytest-timeout
- **User base**: Small (only a few users), no public sign-ups

## Architecture
- FastAPI app with session middleware (`app/app.py`)
- SQLAlchemy models: User, SearchQuery, NotificationSetting, Offer (`app/models.py`)
- Scraper handlers per source site (`app/sources.py`)
- Standalone scraper runner for scheduled execution (`run_scraper.py`)
- Alembic for database migrations
- Templates in `templates/`, static files in `static/`
- Account creation via CLI script (`create_user.py`)

## Scraper Sources
Active (in `HANDLERS` dict in `app/sources.py`):
- OLX (www.olx.pl, m.olx.pl)
- Nieruchomości Online (gdansk.nieruchomosci-online.pl)
- Trojmiasto (ogloszenia.trojmiasto.pl)
- Rentola (rentola.pl)
- Gratka (gratka.pl)

Broken (commented out in `HANDLERS`):
- OtoDom (www.otodom.pl)
- Morizon (www.morizon.pl)

## Testing
- Integration tests in `tests/test_sources.py` hit real websites
- Parametrized: `test_parse_first_page` and `test_pagination` for each source
- Broken sources are `pytest.mark.skip`-ed as placeholders
- Test URLs are kept in `links.txt` for reference
- CI: GitHub Actions workflow (`.github/workflows/test-sources.yml`) runs weekly + manual dispatch

## Development Approach
- Work iteratively and confirm results at each stage
- Preserve existing scraping logic where possible