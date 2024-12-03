from flask import Flask, request, jsonify, render_template
from mongo_service import MongoService
from datetime import datetime
import json
import os

app = Flask(__name__)
mongo_service = MongoService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tips/AddEntry', methods=['POST'])
def add_entry():
    try:
        data = request.json
        print(f"Received data: {data}")  # Debug log
        
        # Convert date from YYYY-MM-DD to DD/MM/YYYY
        input_date = datetime.strptime(data['date'], '%Y-%m-%d')
        formatted_date = input_date.strftime('%d/%m/%Y')
        
        # Calculate total hours from hours and minutes
        total_hours = float(data['hours'] or 0)
        if data.get('minutes'):
            total_hours += float(data['minutes']) / 60
            
        # Format data for mongo_service with default values of 0 for empty tips
        values = [
            formatted_date,  # converted date
            data['name'],
            '',  # placeholder for any additional fields
            total_hours,
            float(data.get('cashTips') or 0),  # Default to 0 if empty
            float(data.get('creditTips') or 0)  # Default to 0 if empty
        ]
        
        print(f"Formatted values: {values}")  # Debug log
        result = mongo_service.append_entry(values)
        return jsonify(result)
    except Exception as e:
        print(f"Error in add_entry: {str(e)}")  # Debug log
        return jsonify({"error": str(e)}), 500

@app.route('/api/tips/daily/<date>')
def get_daily_data(date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        employees = mongo_service.get_employees_for_date(date_obj)
        
        if not employees:
            return jsonify({
                "totalHours": 0,
                "totalCashTips": 0,
                "totalCreditTips": 0,
                "avgTipsPerHour": 0,
                "compensation": 0,
                "employees": []
            })

        MIN_HOURLY_RATE = 50  # Minimum hourly rate in NIS
        
        # Get total hours and tips for the day
        total_hours = sum(e["hours"] for e in employees)
        total_cash_tips = sum(e["cashTips"] for e in employees)
        total_credit_tips = sum(e["creditTips"] for e in employees)
        total_tips = total_cash_tips + total_credit_tips
        
        # Calculate daily average tips per hour
        avg_tips_per_hour = round(total_tips / total_hours, 2) if total_hours > 0 else 0
        
        # Calculate compensation if needed
        compensation_needed = max(0, MIN_HOURLY_RATE - avg_tips_per_hour)
        total_compensation = round(compensation_needed * total_hours, 2)
        
        # Calculate each employee's share
        for emp in employees:
            hours_fraction = emp["hours"] / total_hours if total_hours > 0 else 0
            emp["cashTips"] = round(total_cash_tips * hours_fraction, 2)
            emp["creditTips"] = round(total_credit_tips * hours_fraction, 2)
            emp["totalTips"] = round(emp["cashTips"] + emp["creditTips"], 2)
            emp["compensation"] = round(compensation_needed * emp["hours"], 2)
            emp["finalTotal"] = round(emp["totalTips"] + emp["compensation"], 2)
            emp["effectiveHourly"] = round((emp["finalTotal"] / emp["hours"]) if emp["hours"] > 0 else 0, 2)

        daily_data = {
            "totalHours": round(total_hours, 2),
            "totalCashTips": round(total_cash_tips, 2),
            "totalCreditTips": round(total_credit_tips, 2),
            "totalTips": round(total_tips, 2),
            "avgTipsPerHour": avg_tips_per_hour,
            "compensation": total_compensation,
            "employees": employees
        }
        
        return jsonify(daily_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tips/monthly/<month>')
def get_monthly_data(month):
    try:
        print(f"Processing monthly data for: {month}")  # Debug log
        start_date = datetime.strptime(f"{month}-01", '%Y-%m-%d')
        daily_entries = mongo_service.get_employees_for_month(start_date)
        print(f"Found {len(daily_entries)} entries")  # Debug log
        
        if not daily_entries:
            return jsonify({
                "totalHours": 0,
                "totalCashTips": 0,
                "totalCreditTips": 0,
                "totalCompensation": 0,
                "employeeTotals": []
            })

        MIN_HOURLY_RATE = 50
        
        # Group entries by employee
        employee_totals = {}
        for entry in daily_entries:
            name = entry["name"]
            if name not in employee_totals:
                employee_totals[name] = {
                    "name": name,
                    "hours": 0,
                    "cashTips": 0,
                    "creditTips": 0,
                    "compensation": 0
                }
            
            employee_totals[name]["hours"] += entry["hours"]
            employee_totals[name]["cashTips"] += entry["cashTips"]
            employee_totals[name]["creditTips"] += entry["creditTips"]

        # Calculate totals and compensation
        monthly_total_hours = 0
        monthly_total_cash = 0
        monthly_total_credit = 0
        monthly_total_compensation = 0

        employee_list = []
        for emp in employee_totals.values():
            monthly_total_hours += emp["hours"]
            monthly_total_cash += emp["cashTips"]
            monthly_total_credit += emp["creditTips"]
            
            # Calculate compensation if needed
            emp_total_tips = emp["cashTips"] + emp["creditTips"]
            emp_avg_hourly = emp_total_tips / emp["hours"] if emp["hours"] > 0 else 0
            emp_compensation = max(0, (MIN_HOURLY_RATE - emp_avg_hourly) * emp["hours"])
            
            emp["compensation"] = round(emp_compensation, 2)
            emp["finalTotal"] = round(emp_total_tips + emp_compensation, 2)
            monthly_total_compensation += emp_compensation
            
            # Round all numeric values
            emp["hours"] = round(emp["hours"], 2)
            emp["cashTips"] = round(emp["cashTips"], 2)
            emp["creditTips"] = round(emp["creditTips"], 2)
            
            employee_list.append(emp)

        # Sort employees by final total (highest to lowest)
        employee_list.sort(key=lambda x: x["finalTotal"], reverse=True)

        monthly_data = {
            "totalHours": round(monthly_total_hours, 2),
            "totalCashTips": round(monthly_total_cash, 2),
            "totalCreditTips": round(monthly_total_credit, 2),
            "totalCompensation": round(monthly_total_compensation, 2),
            "employeeTotals": employee_list
        }
        
        print(f"Returning monthly data: {monthly_data}")  # Debug log
        return jsonify(monthly_data)
    except Exception as e:
        print(f"Error in monthly data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/workers')
def get_workers():
    try:
        workers = mongo_service.get_workers()
        return jsonify(workers)
    except Exception as e:
        print(f"Error loading workers: {str(e)}")
        return jsonify([]), 500

@app.route('/api/workers/add', methods=['POST'])
def add_worker():
    try:
        data = request.json
        if not data or 'name' not in data:
            return jsonify({"error": "No name provided"}), 400

        new_name = data['name'].strip()
        if not new_name:
            return jsonify({"error": "Name cannot be empty"}), 400

        workers_file = os.path.join(os.path.dirname(__file__), 'config', 'workers.json')
        with open(workers_file, 'r', encoding='utf-8') as f:
            workers_data = json.load(f)

        if new_name in workers_data['workers']:
            return jsonify({"error": "Worker already exists"}), 400

        workers_data['workers'].append(new_name)
        workers_data['workers'].sort()  # Keep the list alphabetically sorted

        with open(workers_file, 'w', encoding='utf-8') as f:
            json.dump(workers_data, f, indent=4, ensure_ascii=False)

        return jsonify({"message": "Worker added successfully", "workers": workers_data['workers']})
    except Exception as e:
        print(f"Error adding worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tips/AddHours', methods=['POST'])
def add_hours():
    try:
        data = request.json
        print(f"Received hours data: {data}")  # Debug log
        
        # Convert date from YYYY-MM-DD to DD/MM/YYYY
        input_date = datetime.strptime(data['date'], '%Y-%m-%d')
        
        # Calculate total hours from hours and minutes
        total_hours = float(data.get('hours', 0) or 0)
        minutes = float(data.get('minutes', 0) or 0)
        total_hours += minutes / 60
            
        # Format data for mongo_service
        employee_data = {
            'name': data['name'],
            'hours': total_hours,
            'cashTips': 0,  # Initialize with 0
            'creditTips': 0  # Initialize with 0
        }
        
        result = mongo_service.upsert_employee_hours(input_date, employee_data)
        return jsonify({"status": "success", "message": "Hours updated successfully"})
    except Exception as e:
        print(f"Error adding hours: {str(e)}")  # Debug log
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/tips/AddTips', methods=['POST'])
def add_tips():
    try:
        data = request.json
        print(f"Received tips data: {data}")  # Debug log
        
        # Convert empty strings to 0 and handle string to float conversion
        cash_tips = float(data.get('cashTips', 0) or 0)
        credit_tips = float(data.get('creditTips', 0) or 0)
        
        # Convert date from YYYY-MM-DD to DD/MM/YYYY
        input_date = datetime.strptime(data['date'], '%Y-%m-%d')
        
        result = mongo_service.upsert_tips(input_date, cash_tips, credit_tips)
        return jsonify({"status": "success", "message": "Tips updated successfully"})
    except Exception as e:
        print(f"Error adding tips: {str(e)}")  # Debug log
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
