from mongo_service import MongoService
from restaurant_config import RESTAURANTS, get_mongodb_config
from pymongo import MongoClient

def upload_restaurant_configs():
    # Connect directly to MongoDB to access the restaurants collection
    config = get_mongodb_config()
    client = MongoClient(config['uri'])
    db = client[config['db_name']]
    
    # Create or update restaurants collection
    restaurants_collection = db['restaurants']
    
    # Create an index on restaurant_id for faster lookups
    restaurants_collection.create_index('restaurant_id', unique=True)
    
    # Upload each restaurant configuration
    for restaurant_id, config in RESTAURANTS.items():
        restaurant_data = {
            'restaurant_id': restaurant_id,
            **config  # Include all configuration data
        }
        
        # Upsert the restaurant configuration
        restaurants_collection.update_one(
            {'restaurant_id': restaurant_id},
            {'$set': restaurant_data},
            upsert=True
        )
        
        print(f"Uploaded configuration for {restaurant_id}")
    
    print("All restaurant configurations uploaded successfully")

if __name__ == "__main__":
    upload_restaurant_configs() 