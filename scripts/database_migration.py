from datetime import datetime
import logging
from pymongo import MongoClient
from tqdm import tqdm  # For progress bars

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)

class DatabaseMigration:
    def __init__(self, mongodb_uri):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client.get_default_database()
        self.logger = logging.getLogger(__name__)

    def backup_collections(self):
        """Create backup of critical collections"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            for collection in self.db.list_collection_names():
                if any(x in collection for x in ['dailyEntries', 'workers', 'activeShifts']):
                    backup_name = f"{collection}_backup_{timestamp}"
                    self.logger.info(f"Backing up {collection} to {backup_name}")
                    self.db[collection].aggregate([
                        {"$out": backup_name}
                    ])
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            return False

    def migrate_restaurant_data(self):
        """Add restaurant_id to existing collections"""
        try:
            restaurants = list(self.db.restaurants.find({}))
            self.logger.info(f"Found {len(restaurants)} restaurants to process")

            for restaurant in tqdm(restaurants, desc="Processing restaurants"):
                restaurant_id = restaurant['restaurant_id']
                
                # Collections to update
                collections = [
                    f"{restaurant_id}_dailyEntries",
                    f"{restaurant_id}_activeShifts",
                    f"{restaurant_id}_workers"
                ]

                for collection in collections:
                    if collection in self.db.list_collection_names():
                        self.logger.info(f"Adding restaurant_id to {collection}")
                        self.db[collection].update_many(
                            {"restaurant_id": {"$exists": False}},
                            {"$set": {"restaurant_id": restaurant_id}}
                        )

            return True
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            return False

    def create_unified_collections(self):
        """Create and populate new unified collections"""
        try:
            # Create indexes for new collections
            self.db.unified_workers.create_index([
                ("worker_id", 1),
                ("restaurant_id", 1)
            ], unique=True)

            self.db.unified_dailyEntries.create_index([
                ("restaurant_id", 1),
                ("date", 1)
            ], unique=True)

            # Migrate workers data
            restaurants = list(self.db.restaurants.find({}))
            for restaurant in tqdm(restaurants, desc="Migrating workers"):
                restaurant_id = restaurant['restaurant_id']
                old_collection = f"{restaurant_id}_workers"
                
                if old_collection in self.db.list_collection_names():
                    workers_doc = self.db[old_collection].find_one({})
                    if workers_doc and 'workers' in workers_doc:
                        for worker_name in workers_doc['workers']:
                            self.db.unified_workers.update_one(
                                {
                                    "name": worker_name,
                                    "restaurant_id": restaurant_id
                                },
                                {
                                    "$set": {
                                        "active": True,
                                        "created_at": datetime.utcnow(),
                                        "migrated_from": old_collection
                                    }
                                },
                                upsert=True
                            )

            # Migrate daily entries
            for restaurant in tqdm(restaurants, desc="Migrating daily entries"):
                restaurant_id = restaurant['restaurant_id']
                old_collection = f"{restaurant_id}_dailyEntries"
                
                if old_collection in self.db.list_collection_names():
                    cursor = self.db[old_collection].find({})
                    for doc in cursor:
                        doc['restaurant_id'] = restaurant_id
                        doc['migrated_at'] = datetime.utcnow()
                        doc['migrated_from'] = old_collection
                        
                        self.db.unified_dailyEntries.update_one(
                            {
                                "restaurant_id": restaurant_id,
                                "date": doc['date']
                            },
                            {"$set": doc},
                            upsert=True
                        )

            return True
        except Exception as e:
            self.logger.error(f"Unified collections creation failed: {str(e)}")
            return False

    def verify_migration(self):
        """Verify data integrity after migration"""
        try:
            restaurants = list(self.db.restaurants.find({}))
            all_valid = True

            for restaurant in tqdm(restaurants, desc="Verifying migration"):
                restaurant_id = restaurant['restaurant_id']
                
                # Verify workers
                old_workers = self.db[f"{restaurant_id}_workers"].find_one({})
                new_workers = list(self.db.unified_workers.find({"restaurant_id": restaurant_id}))
                
                if old_workers and 'workers' in old_workers:
                    if len(old_workers['workers']) != len(new_workers):
                        self.logger.error(f"Worker count mismatch for {restaurant_id}")
                        all_valid = False

                # Verify daily entries
                old_entries = self.db[f"{restaurant_id}_dailyEntries"].count_documents({})
                new_entries = self.db.unified_dailyEntries.count_documents({"restaurant_id": restaurant_id})
                
                if old_entries != new_entries:
                    self.logger.error(f"Daily entries count mismatch for {restaurant_id}")
                    all_valid = False

            return all_valid
        except Exception as e:
            self.logger.error(f"Verification failed: {str(e)}")
            return False

    def migrate_workers_schema(self, restaurant_id):
        """Migrate worker collection schema without merging"""
        collection = self.db[f"{restaurant_id}_workers"]
        
        # Get current workers
        old_doc = collection.find_one({})
        if old_doc and 'workers' in old_doc:
            # Create new documents for each worker
            for worker_name in old_doc['workers']:
                collection.insert_one({
                    "name": worker_name,
                    "active": True,
                    "created_at": datetime.utcnow(),
                    "wage_info": {
                        "base_wage": None,  # To be filled manually
                        "tip_participation": True
                    }
                })
            # Archive old format
            collection.rename(f"{restaurant_id}_workers_old")

    def migrate_shifts_schema(self, restaurant_id):
        """Migrate shifts collection schema without merging"""
        collection = self.db[f"{restaurant_id}_activeShifts"]
        
        # Get current active shifts
        current_shifts = collection.find({})
        
        # Create new collection with updated schema
        new_collection = self.db[f"{restaurant_id}_active_shifts"]
        
        for shift in current_shifts:
            new_collection.insert_one({
                "worker_name": shift.get('worker_name'),
                "start_time": shift.get('start_time'),
                "end_time": shift.get('end_time', None),
                "status": "active" if not shift.get('end_time') else "completed",
                "created_at": shift.get('created_at', datetime.utcnow()),
                "updated_at": datetime.utcnow()
            })
        
        # Optionally archive old collection
        if collection.count_documents({}) > 0:
            collection.rename(f"{restaurant_id}_activeShifts_old")

def main():
    # Load from environment or config
    MONGODB_URI = "your_mongodb_uri_here"
    
    migration = DatabaseMigration(MONGODB_URI)
    
    # Step 1: Backup
    if not migration.backup_collections():
        migration.logger.error("Backup failed, aborting migration")
        return

    # Step 2: Add restaurant_id to existing collections
    if not migration.migrate_restaurant_data():
        migration.logger.error("Restaurant data migration failed")
        return

    # Step 3: Create and populate unified collections
    if not migration.create_unified_collections():
        migration.logger.error("Unified collections creation failed")
        return

    # Step 4: Verify migration
    if migration.verify_migration():
        migration.logger.info("Migration completed successfully")
    else:
        migration.logger.error("Migration verification failed")

if __name__ == "__main__":
    main() 