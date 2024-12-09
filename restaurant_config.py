from os import getenv
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = getenv('MONGODB_URI')
MONGODB_DB_NAME = getenv('MONGODB_DB_NAME', 'tipsManagementDB')

RESTAURANTS = {
    'dama': {
        'name': 'Dama Restaurant',
        'min_hourly_rate': {
            'default': 50,
            'saturday_multiplier': 1.5  # Changed from fixed 75 to 1.5x multiplier
        },
        'compensation_type': 'round_up'  # Default behavior
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

def get_restaurant_config(restaurant_id):
    return RESTAURANTS.get(restaurant_id)

def get_mongodb_config():
    return {
        'uri': MONGODB_URI,
        'db_name': MONGODB_DB_NAME
    }
