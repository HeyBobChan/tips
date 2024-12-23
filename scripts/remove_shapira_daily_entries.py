import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from mongo_service import MongoService
from pymongo import MongoClient

def remove_shapira_daily_entries():
    # Initialize MongoDB service for Shapira restaurant
    mongo_service = MongoService.get_instance('shapira')
    
    # Get the current month's start and end dates
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_date = datetime(today.year + 1, 1, 1)
    else:
        end_date = datetime(today.year, today.month + 1, 1)
    
    # Remove all entries for the current month
    result = mongo_service.db[mongo_service.get_collection_name('dailyEntries')].delete_many({
        "date": {
            "$gte": start_date,
            "$lt": end_date
        }
    })
    
    print(f"Removed {result.deleted_count} daily entries for Shapira restaurant for {today.strftime('%B %Y')}")

if __name__ == "__main__":
    remove_shapira_daily_entries() 