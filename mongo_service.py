from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from restaurant_config import get_restaurant_config, get_mongodb_config

class MongoService:
    def __init__(self, restaurant_id):
        mongodb_config = get_mongodb_config()
        if not mongodb_config['uri']:
            raise ValueError("No MongoDB connection string found in environment variables")
            
        restaurant_config = get_restaurant_config(restaurant_id)
        if not restaurant_config:
            raise ValueError(f"Invalid restaurant ID: {restaurant_id}")

        try:
            self.client = MongoClient(mongodb_config['uri'], serverSelectionTimeoutMS=5000)
            self.client.server_info()
            print(f"Successfully connected to MongoDB Atlas for {restaurant_config['name']}")
            
            self.db = self.client[mongodb_config['db_name']]
            self.restaurant_id = restaurant_id
            
        except Exception as e:
            print(f"Failed to connect to MongoDB Atlas: {str(e)}")
            raise

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

    def upsert_employee_hours(self, date, employee_data):
        """Update or insert employee hours for a specific date"""
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
                    }
                )
            else:
                # Add new employee to existing date
                self.db[self.get_collection_name('dailyEntries')].update_one(
                    {"date": date},
                    {"$push": {"employees": employee_data}}
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
            self.db[self.get_collection_name('dailyEntries')].insert_one(entry)
        
        return {"status": "success"}
