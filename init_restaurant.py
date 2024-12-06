from mongo_service import MongoService
from restaurant_config import RESTAURANTS

def init_restaurant(restaurant_id, initial_workers=None):
    if restaurant_id not in RESTAURANTS:
        print(f"Error: Restaurant '{restaurant_id}' not found in config")
        return
    
    if initial_workers is None:
        initial_workers = []  # Empty list if no workers provided
    
    try:
        mongo_service = MongoService(restaurant_id)
        collection_name = mongo_service.get_collection_name('workers')
        
        # Check if workers collection already exists
        existing = mongo_service.db[collection_name].find_one({})
        if existing:
            print(f"Workers collection already exists for {restaurant_id}")
            return
        
        # Initialize workers collection
        mongo_service.db[collection_name].insert_one({
            "workers": initial_workers
        })
        
        print(f"Successfully initialized workers for {restaurant_id}")
        
    except Exception as e:
        print(f"Error initializing restaurant: {str(e)}")

if __name__ == "__main__":
  
    record_workers = []
    init_restaurant('Record', record_workers) 