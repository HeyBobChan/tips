from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from restaurant_config import get_restaurant_config, get_mongodb_config
from pymongo.errors import ConnectionFailure, OperationFailure
from tenacity import retry, stop_after_attempt, wait_exponential
from contextlib import contextmanager

class MongoService:
    _instances = {}  # Class-level dictionary to store instances
    _client = None   # Class-level shared client
    _config = None   # Class-level config

    @classmethod
    def get_instance(cls, restaurant_id):
        """Singleton pattern to reuse connections"""
        if restaurant_id not in cls._instances:
            cls._instances[restaurant_id] = cls(restaurant_id)
        return cls._instances[restaurant_id]

    def __init__(self, restaurant_id):
        if not MongoService._client:
            MongoService._config = get_mongodb_config()
            if not MongoService._config['uri']:
                raise ValueError("No MongoDB connection string found")
                
            # Initialize shared client with connection pooling
            MongoService._client = MongoClient(
                MongoService._config['uri'],
                serverSelectionTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=5,
                maxIdleTimeMS=60000,
                retryWrites=True
            )
        
        self.client = MongoService._client
        self.db = self.client[MongoService._config['db_name']]
        self.restaurant_id = restaurant_id

    def get_collection_name(self, base_name):
        """Helper method to generate restaurant-specific collection names"""
        return f"{self.restaurant_id}_{base_name}"

    def append_entry(self, values):
        date_obj = datetime.strptime(values[0], '%d/%m/%Y')
        employee_name = values[1]
        
        entry = {
            "date": date_obj,
            "totalHours": float(values[3]),
            "totalCashTips": float(values[4]),
            "totalCreditTips": float(values[5]),
            "employees": [{
                "name": employee_name,
                "hours": float(values[3]),
                "cashTips": float(values[4]),
                "creditTips": float(values[5])
            }]
        }
        
        # Try to find existing entry for this date
        existing = self.db[self.get_collection_name('dailyEntries')].find_one({"date": date_obj})
        
        if existing:
            # Check if employee exists for this date
            employee_exists = False
            for emp in existing["employees"]:
                if emp["name"] == employee_name:
                    employee_exists = True
                    break
            
            if employee_exists:
                # Update existing employee's data
                self.db[self.get_collection_name('dailyEntries')].update_one(
                    {
                        "date": date_obj,
                        "employees.name": employee_name
                    },
                    {
                        "$set": {
                            "employees.$": entry["employees"][0]
                        }
                    }
                )
            else:
                # Add new employee to existing date
                self.db[self.get_collection_name('dailyEntries')].update_one(
                    {"date": date_obj},
                    {"$push": {"employees": entry["employees"][0]}}
                )
        else:
            # Create new entry
            self.db[self.get_collection_name('dailyEntries')].insert_one(entry)
            
        return {"status": "success"}

    def get_employees_for_date(self, date):
        """Example of using restaurant-specific collection"""
        collection = self.db[self.get_collection_name('dailyEntries')]
        # Convert string date to datetime if needed
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d')
        entry = collection.find_one({"date": date})
        return entry['employees'] if entry else []

    def get_workers(self):
        """Example of using restaurant-specific collection"""
        collection = self.db[self.get_collection_name('workers')]
        workers_doc = collection.find_one({})
        return workers_doc['workers'] if workers_doc else []

    def get_employees_for_month(self, start_date):
        # Get the first and last day of the month
        month_start = start_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        # Query for all entries in this date range
        entries = self.db[self.get_collection_name('dailyEntries')].find({
            "date": {
                "$gte": month_start,
                "$lt": month_end
            }
        })

        # Flatten the employee data with dates
        result = []
        for entry in entries:
            # Skip entries that don't have employees data
            if "employees" not in entry or not entry["employees"]:
                continue
            
            for emp in entry["employees"]:
                emp_data = emp.copy()
                emp_data["date"] = entry["date"]
                result.append(emp_data)

        return result

    def upsert_tips(self, date, cash_tips, credit_tips):
        """Update or insert tips for a specific date"""
        # Get existing entry to calculate proportions
        existing = self.db[self.get_collection_name('dailyEntries')].find_one({"date": date})
        
        if existing and existing.get("employees"):
            total_hours = sum(emp["hours"] for emp in existing["employees"])
            
            # Calculate each employee's share based on their hours
            updated_employees = []
            for emp in existing["employees"]:
                hours_fraction = emp["hours"] / total_hours if total_hours > 0 else 0
                emp_cash = round(cash_tips * hours_fraction, 2)
                emp_credit = round(credit_tips * hours_fraction, 2)
                
                updated_employees.append({
                    "name": emp["name"],
                    "hours": emp["hours"],
                    "cashTips": emp_cash,
                    "creditTips": emp_credit,
                    "compensation": emp.get("compensation", 0)
                })
            
            # Update the entire document
            return self.db[self.get_collection_name('dailyEntries')].update_one(
                {"date": date},
                {
                    "$set": {
                        "totalCashTips": cash_tips,
                        "totalCreditTips": credit_tips,
                        "employees": updated_employees
                    }
                },
                upsert=True
            )
        else:
            # If no existing entry, just set the totals
            return self.db[self.get_collection_name('dailyEntries')].update_one(
                {"date": date},
                {
                    "$set": {
                        "totalCashTips": cash_tips,
                        "totalCreditTips": credit_tips
                    }
                },
                upsert=True
            )

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations"""
        session = None
        try:
            session = self.client.start_session()
            yield session
        except Exception as e:
            if session:
                session.abort_transaction()
            raise
        finally:
            if session:
                session.end_session()

    def upsert_employee_hours(self, date, employee_data, session=None):
        """Update or insert employee hours for a specific date"""
        try:
            # Try to find existing entry for this date
            existing = self.db[self.get_collection_name('dailyEntries')].find_one({"date": date})
            
            if existing:
                # Check if employee exists for this date
                employee_exists = False
                for emp in existing["employees"]:
                    if emp["name"] == employee_data["name"]:
                        employee_exists = True
                        break
                
                if employee_exists:
                    # Update existing employee's hours
                    self.db[self.get_collection_name('dailyEntries')].update_one(
                        {
                            "date": date,
                            "employees.name": employee_data["name"]
                        },
                        {
                            "$set": {
                                "employees.$.hours": employee_data["hours"]
                            }
                        },
                        session=session
                    )
                else:
                    # Add new employee to existing date
                    self.db[self.get_collection_name('dailyEntries')].update_one(
                        {"date": date},
                        {"$push": {"employees": employee_data}},
                        session=session
                    )
            else:
                # Create new entry
                entry = {
                    "date": date,
                    "totalHours": employee_data["hours"],
                    "totalCashTips": 0,
                    "totalCreditTips": 0,
                    "employees": [employee_data]
                }
                self.db[self.get_collection_name('dailyEntries')].insert_one(entry, session=session)
            
            return {"status": "success"}
        except Exception as e:
            print(f"Error in upsert_employee_hours: {str(e)}")
            raise
