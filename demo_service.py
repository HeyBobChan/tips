import json
from datetime import datetime
import os

class DemoService:
    def __init__(self):
        self.data_file = 'demo_data.json'
        self._ensure_data_file()

    def _ensure_data_file(self):
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w') as f:
                json.dump({}, f)

    def _load_data(self):
        with open(self.data_file, 'r') as f:
            return json.load(f)

    def _save_data(self, data):
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

    def append_entry(self, values):
        data = self._load_data()
        
        # Extract date and create sheet name (month-year)
        date = datetime.strptime(values[0], '%d/%m/%Y')
        sheet_name = date.strftime('%m-%Y')
        
        # Initialize sheet if it doesn't exist
        if sheet_name not in data:
            data[sheet_name] = []
        
        # Append the entry
        data[sheet_name].append(values)
        self._save_data(data)
        
        return {"status": "success"}

    def get_employees_for_date(self, date):
        data = self._load_data()
        sheet_name = date.strftime('%m-%Y')
        date_str = date.strftime('%d/%m/%Y')
        
        if sheet_name not in data:
            return []
        
        employees = []
        for row in data[sheet_name]:
            if len(row) >= 6 and row[0] == date_str:
                employees.append({
                    "name": row[1],
                    "hours": float(row[3]),
                    "cashTips": float(row[4]),
                    "creditTips": float(row[5])
                })
        
        return employees

    def get_employees_for_month(self, start_date):
        data = self._load_data()
        sheet_name = start_date.strftime('%m-%Y')
        
        if sheet_name not in data:
            return []
        
        employees = []
        for row in data[sheet_name]:
            if len(row) >= 6:
                try:
                    employees.append({
                        "date": row[0],
                        "name": row[1],
                        "hours": float(row[3]),
                        "cashTips": float(row[4]),
                        "creditTips": float(row[5])
                    })
                except (ValueError, IndexError):
                    continue
        
        return employees 