from os import getenv
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = getenv('MONGODB_URI')
MONGODB_DB_NAME = getenv('MONGODB_DB_NAME', 'tipsManagementDB')

# Legacy configuration - will be moved to MongoDB
RESTAURANTS = {
    'dama': {
        'name': 'Dama Restaurant',
        'min_hourly_rate': {
            'default': 50,
            'saturday_multiplier': 1.5
        },
        'compensation_type': 'round_up'
    },
    'anan': {
        'name': 'Anan Restaurant',
        'min_hourly_rate': 80,
        'compensation_type': 'round_up'
    },
    'test': {
        'name': 'Test Restaurant',
        'min_hourly_rate': 50,
        'compensation_type': 'round_up'
    },
    'additive_test': {
        'name': 'Additive Test Restaurant',
        'min_hourly_rate': 40,
        'compensation_type': 'additive'
    },
    'shapira': {
        'name': 'Shapira Restaurant',
        'min_hourly_rate': {
            'default': 40,
            'saturday_multiplier': 1.5
        },
        'compensation_type': 'additive',
        'tips_threshold': 10,
        'tips_type': 'threshold',
        'hidden': True
    }
}

_mongo_client = None
_mongo_db = None

def _get_db():
    global _mongo_client, _mongo_db
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGODB_URI)
        _mongo_db = _mongo_client[MONGODB_DB_NAME]
    return _mongo_db

def get_restaurant_config(restaurant_id):
    """Get restaurant configuration from MongoDB"""
    db = _get_db()
    restaurant = db.restaurants.find_one({'restaurant_id': restaurant_id})
    if restaurant:
        # Remove MongoDB _id field
        restaurant.pop('_id', None)
        restaurant.pop('restaurant_id', None)
        return restaurant
    return None

def get_all_restaurants():
    """Get all restaurant configurations from MongoDB"""
    db = _get_db()
    restaurants = {}
    for restaurant in db.restaurants.find({'hidden': {'$ne': True}}):
        restaurant_id = restaurant.pop('restaurant_id')
        restaurant.pop('_id', None)
        restaurants[restaurant_id] = restaurant
    return restaurants

def create_restaurant(restaurant_id, config):
    """Create a new restaurant configuration in MongoDB"""
    db = _get_db()
    restaurant_data = {
        'restaurant_id': restaurant_id,
        **config
    }
    db.restaurants.update_one(
        {'restaurant_id': restaurant_id},
        {'$set': restaurant_data},
        upsert=True
    )
    return restaurant_data

def update_restaurant(restaurant_id, config):
    """Update an existing restaurant configuration in MongoDB"""
    return create_restaurant(restaurant_id, config)

def delete_restaurant(restaurant_id):
    """Delete a restaurant configuration from MongoDB"""
    db = _get_db()
    result = db.restaurants.delete_one({'restaurant_id': restaurant_id})
    return result.deleted_count > 0

def get_mongodb_config():
    return {
        'uri': MONGODB_URI,
        'db_name': MONGODB_DB_NAME
    }
