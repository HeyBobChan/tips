from os import getenv
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = getenv('MONGODB_URI')
MONGODB_DB_NAME = getenv('MONGODB_DB_NAME', 'tipsManagementDB')

RESTAURANTS = {
    'dama': {
        'name': 'Dama Restaurant',
        'min_hourly_rate': 50
    },
    'anan': {
        'name': 'Anan Restaurant',
        'min_hourly_rate': 50
    }
}

def get_restaurant_config(restaurant_id):
    return RESTAURANTS.get(restaurant_id)

def get_mongodb_config():
    return {
        'uri': MONGODB_URI,
        'db_name': MONGODB_DB_NAME
    } 