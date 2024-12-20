from restaurant_config import get_mongodb_config
from pymongo import MongoClient

def migrate_layout_type():
    # Connect to MongoDB
    config = get_mongodb_config()
    client = MongoClient(config['uri'])
    db = client[config['db_name']]
    
    # Get all restaurants
    restaurants = db.restaurants.find({})
    
    # Add layout_type if missing
    for restaurant in restaurants:
        if 'layout_type' not in restaurant:
            db.restaurants.update_one(
                {'_id': restaurant['_id']},
                {'$set': {'layout_type': 'open'}}  # Default to 'open' layout
            )
            print(f"Added layout_type to {restaurant.get('name', restaurant.get('restaurant_id'))}")
    
    print("Migration complete")

if __name__ == "__main__":
    migrate_layout_type() 