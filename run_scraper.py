#!/usr/bin/env python3
"""
Main scraping script that processes all active queries and sends notifications.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Any
import requests
import json

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.orm import sessionmaker
from database import engine
from models import User, SearchQuery, NotificationSetting, Offer
from scraper import scrape_query


def send_discord_notification(webhook_url: str, new_offers: List[Offer], query_name: str) -> bool:
    """Send Discord notification for new offers."""
    try:
        # Create embed for each offer (max 10 embeds per message)
        embeds = []
        for i, offer in enumerate(new_offers[:10]):
            embeds.append({
                "title": offer.title[:256],  # Discord embed title limit
                "url": offer.url,
                "color": 0x00ff00,  # Green color
                "footer": {
                    "text": f"Query: {query_name}"
                }
            })
        
        # Create the main message
        content = f"🏠 **{len(new_offers)} new rental listing{'s' if len(new_offers) != 1 else ''} found!**"
        if len(new_offers) > 10:
            content += f"\n_(Showing first 10 of {len(new_offers)} offers)_"
        
        payload = {
            "content": content,
            "embeds": embeds
        }
        
        response = requests.post(webhook_url,
                               json=payload,
                               headers={'Content-Type': 'application/json'},
                               timeout=10)
        
        return response.status_code == 204
        
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")
        return False


def process_query(db_session, query: SearchQuery) -> Dict[str, Any]:
    """Process a single search query and return results."""
    print(f"Processing query: {query.name} (ID: {query.id})")
    
    # Check if this is the first run (never scraped before)
    is_first_run = query.last_scraped_at is None
    
    result = {
        "query_id": query.id,
        "query_name": query.name,
        "success": False,
        "new_offers": [],
        "total_offers": 0,
        "error": None,
        "is_first_run": is_first_run
    }
    
    try:
        # Scrape the query
        offers = scrape_query(query.url)
        result["total_offers"] = len(offers)
        
        print(f"  Found {len(offers)} offers")
        
        # Check for new offers (not in database yet)
        new_offers = []
        for offer in offers:
            existing = db_session.query(Offer).filter(Offer.url == offer.url).first()
            if not existing:
                # Create new offer record
                new_offer = Offer(
                    title=offer.title,
                    url=offer.url,
                    user_id=query.user_id,
                    query_id=query.id
                )
                db_session.add(new_offer)
                new_offers.append(new_offer)
        
        result["new_offers"] = new_offers
        result["success"] = True
        
        print(f"  {len(new_offers)} new offers")
        if is_first_run:
            print(f"  (First run - will not send notifications)")
        
        # Update query status
        query.last_scraped_at = datetime.utcnow()
        query.last_scrape_count = len(offers)
        
        if len(offers) > 0:
            query.last_scrape_status = "success"
        else:
            query.last_scrape_status = "no_results"
        
        query.last_scrape_error = None
        
        # Commit changes for this query immediately to ensure independence
        db_session.commit()
        print(f"  Query {query.id} completed and committed")
        
    except Exception as e:
        error_msg = str(e)
        print(f"  ERROR: {error_msg}")
        
        result["error"] = error_msg
        
        # Update query status
        query.last_scraped_at = datetime.utcnow()
        query.last_scrape_count = 0
        query.last_scrape_status = "error"
        query.last_scrape_error = error_msg
        
        # Commit the error state
        try:
            db_session.commit()
            print(f"  Query {query.id} error state committed")
        except Exception as commit_error:
            print(f"  Failed to commit error state: {commit_error}")
            db_session.rollback()
    
    return result


def main():
    """Main scraping function."""
    print(f"Starting scraping run at {datetime.now()}")
    
    # Create database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get all active queries
        active_queries = db.query(SearchQuery).filter(SearchQuery.is_active == True).all()
        
        print(f"Found {len(active_queries)} active queries")
        
        if not active_queries:
            print("No active queries to process")
            return
        
        # Group queries by user for notification purposes
        users_with_new_offers = {}
        
        # Process each query
        for query in active_queries:
            result = process_query(db, query)
            
            # If there are new offers AND it's not the first run, group them by user for notifications
            if result["success"] and result["new_offers"] and not result["is_first_run"]:
                user_id = query.user_id
                if user_id not in users_with_new_offers:
                    users_with_new_offers[user_id] = []
                
                users_with_new_offers[user_id].append({
                    "query": query,
                    "new_offers": result["new_offers"]
                })
        
        # Note: Individual query results are already committed in process_query()
        print("All queries processed")
        
        # Send notifications
        for user_id, query_results in users_with_new_offers.items():
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                continue
                
            print(f"Sending notifications for user: {user.username}")
            
            # Get active notification settings for this user
            notification_settings = db.query(NotificationSetting).filter(
                NotificationSetting.user_id == user_id,
                NotificationSetting.is_active == True
            ).all()
            
            # Send notification for each query with new offers
            for query_result in query_results:
                query = query_result["query"]
                new_offers = query_result["new_offers"]
                
                print(f"  {len(new_offers)} new offers for query: {query.name}")
                
                # Send to each active notification channel
                for notification in notification_settings:
                    if notification.discord_webhook_url:
                        success = send_discord_notification(
                            notification.discord_webhook_url,
                            new_offers,
                            query.name
                        )
                        if success:
                            print(f"    ✓ Discord notification sent")
                        else:
                            print(f"    ✗ Discord notification failed")
        
        print(f"Scraping run completed at {datetime.now()}")
        
    except Exception as e:
        print(f"Fatal error during scraping: {e}")
        # Individual queries already handle their own commits/rollbacks
    finally:
        db.close()


if __name__ == "__main__":
    main()