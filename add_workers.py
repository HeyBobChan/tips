from mongo_service import MongoService
from restaurant_config import RESTAURANTS

def get_workers(restaurant_id):
    """Get current workers for a restaurant"""
    if restaurant_id not in RESTAURANTS:
        print(f"Error: Restaurant '{restaurant_id}' not found in config")
        return []
        
    try:
        mongo_service = MongoService(restaurant_id)
        collection_name = mongo_service.get_collection_name('workers')
        print(f"Using collection: {collection_name}")
        
        workers = mongo_service.get_workers()
        print(f"Current workers for {restaurant_id}:", workers)
        return workers
    except Exception as e:
        print(f"Error getting workers: {str(e)}")
        return []

def add_workers(restaurant_id, new_workers):
    """Add new workers to a restaurant"""
    if restaurant_id not in RESTAURANTS:
        print(f"Error: Restaurant '{restaurant_id}' not found in config")
        return
        
    try:
        mongo_service = MongoService(restaurant_id)
        collection_name = mongo_service.get_collection_name('workers')
        print(f"Using collection: {collection_name}")
        
        # Get current workers or initialize if not exists
        workers_doc = mongo_service.db[collection_name].find_one({})
        if not workers_doc:
            workers_doc = {"workers": []}
            mongo_service.db[collection_name].insert_one(workers_doc)
        
        current_workers = workers_doc['workers']
        
        # Add new workers (avoiding duplicates)
        added_workers = []
        for worker in new_workers:
            if worker not in current_workers:
                current_workers.append(worker)
                added_workers.append(worker)
        
        if added_workers:
            # Update the collection
            mongo_service.db[collection_name].update_one(
                {}, 
                {"$set": {"workers": current_workers}}
            )
            print(f"Successfully added workers to {restaurant_id}:", added_workers)
        else:
            print("No new workers to add (all already exist)")
        
        print("Current workers:", current_workers)
        
    except Exception as e:
        print(f"Error adding workers: {str(e)}")

def remove_workers(restaurant_id, workers_to_remove):
    """Remove workers from a restaurant"""
    if restaurant_id not in RESTAURANTS:
        print(f"Error: Restaurant '{restaurant_id}' not found in config")
        return
        
    try:
        mongo_service = MongoService(restaurant_id)
        collection_name = mongo_service.get_collection_name('workers')
        print(f"Using collection: {collection_name}")
        
        # Get current workers or initialize if not exists
        workers_doc = mongo_service.db[collection_name].find_one({})
        if not workers_doc:
            print(f"No workers collection found for {restaurant_id}")
            return
        
        current_workers = workers_doc['workers']
        
        # Remove workers
        removed_workers = []
        for worker in workers_to_remove:
            if worker in current_workers:
                current_workers.remove(worker)
                removed_workers.append(worker)
        
        if removed_workers:
            # Update the collection
            mongo_service.db[collection_name].update_one(
                {}, 
                {"$set": {"workers": current_workers}}
            )
            print(f"Successfully removed workers from {restaurant_id}:", removed_workers)
        else:
            print("No workers found to remove")
        
        print("Current workers:", current_workers)
        
    except Exception as e:
        print(f"Error removing workers: {str(e)}")

def main():
    while True:
        # Select restaurant
        print("\nAvailable restaurants:")
        restaurants = list(RESTAURANTS.items())
        for i, (id, info) in enumerate(restaurants, 1):
            print(f"{i}. {info['name']} ({id})")
        print("0. Exit")
        
        try:
            choice = int(input("\nSelect restaurant number (0 to exit): "))
            if choice == 0:
                break
            if choice < 1 or choice > len(restaurants):
                print("Invalid choice. Please try again.")
                continue
            
            restaurant_id = restaurants[choice-1][0]
            
            # Show current workers
            print("\nGetting current workers...")
            current_workers = get_workers(restaurant_id)
            
            # Select action
            print("\nSelect action:")
            print("1. Add workers")
            print("2. Remove workers")
            print("0. Back to restaurant selection")
            
            action = int(input("\nSelect action number: "))
            
            if action == 0:
                continue
            elif action == 1:
                # Add workers
                print("\nEnter new worker names (comma-separated):")
                new_names = input().strip()
                if new_names:
                    new_workers = [name.strip() for name in new_names.split(',')]
                    add_workers(restaurant_id, new_workers)
            elif action == 2:
                # Remove workers
                if not current_workers:
                    print("No workers to remove!")
                    continue
                    
                print("\nCurrent workers:")
                for i, worker in enumerate(current_workers, 1):
                    print(f"{i}. {worker}")
                
                print("\nEnter numbers of workers to remove (comma-separated):")
                selections = input().strip()
                if selections:
                    try:
                        indices = [int(i.strip())-1 for i in selections.split(',')]
                        workers_to_remove = [current_workers[i] for i in indices if 0 <= i < len(current_workers)]
                        remove_workers(restaurant_id, workers_to_remove)
                    except (ValueError, IndexError):
                        print("Invalid selection. Please try again.")
            else:
                print("Invalid choice. Please try again.")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 