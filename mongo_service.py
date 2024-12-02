from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

class MongoService:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get MongoDB connection string from environment variable
        MONGODB_URI = os.getenv('MONGODB_URI')
        if not MONGODB_URI:
            raise ValueError("No MongoDB connection string found in environment variables")
            
        try:
            self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Test the connection
            self.client.server_info()
            print("Successfully connected to MongoDB Atlas")
            self.db = self.client['tipsManagementDB']
        except Exception as e:
            print(f"Failed to connect to MongoDB Atlas: {str(e)}")
            raise
        
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
        existing = self.db.dailyEntries.find_one({"date": date_obj})
        
        if existing:
            # Check if employee exists for this date
            employee_exists = False
            for emp in existing["employees"]:
                if emp["name"] == employee_name:
                    employee_exists = True
                    break
            
            if employee_exists:
                # Update existing employee's data
                self.db.dailyEntries.update_one(
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
                self.db.dailyEntries.update_one(
                    {"date": date_obj},
                    {"$push": {"employees": entry["employees"][0]}}
                )
        else:
            # Create new entry
            self.db.dailyEntries.insert_one(entry)
            
        return {"status": "success"}

    def get_employees_for_date(self, date):
        entry = self.db.dailyEntries.find_one({"date": date})
        if not entry:
            return []
        return entry["employees"]

    def get_workers(self):
        workers_doc = self.db.workers.find_one()
        return workers_doc["workers"] if workers_doc else [] 

    def get_employees_for_month(self, start_date):
        # Get the first and last day of the month
        month_start = start_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        # Query for all entries in this date range
        entries = self.db.dailyEntries.find({
            "date": {
                "$gte": month_start,
                "$lt": month_end
            }
        })

        # Flatten the employee data with dates
        result = []
        for entry in entries:
            for emp in entry["employees"]:
                emp_data = emp.copy()
                emp_data["date"] = entry["date"]
                result.append(emp_data)

        return result 

    def upsert_tips(self, date, cash_tips, credit_tips):
        """Update or insert tips for a specific date"""
        # Get existing entry to calculate proportions
        existing = self.db.dailyEntries.find_one({"date": date})
        
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
            return self.db.dailyEntries.update_one(
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
            return self.db.dailyEntries.update_one(
                {"date": date},
                {
                    "$set": {
                        "totalCashTips": cash_tips,
                        "totalCreditTips": credit_tips
                    }
                },
                upsert=True
            )
