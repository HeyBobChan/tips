from flask import Flask, request, jsonify, render_template, session
from mongo_service import MongoService
from datetime import datetime
import json
import os
from restaurant_config import get_restaurant_config, RESTAURANTS
from functools import wraps
import atexit
from openai import OpenAI
import time
import tempfile
import re
from datetime import datetime, timedelta


def wait_on_run(run, thread):
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

def clean_response(text):
    # Remove patterns like '【...†...】'
    cleaned_text = re.sub(r'【[^】]*?†[^】]*?】', '', text)
    # Optionally, remove any other markers if needed
    cleaned_text = re.sub(r'[\[\]]', '', cleaned_text)
    # Strip leading and trailing whitespace
    return cleaned_text.strip()

def get_assistant_response(user_input="", image_data=None):
    if 'thread_id' not in session:
        session['thread_id'] = client.beta.threads.create().id

    message_content = []
    
    if (user_input):
        message_content.append({"type": "text", "text": user_input})
    
    if image_data:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(image_data)
            temp_file_path = temp_file.name

        # Upload the file to OpenAI
        with open(temp_file_path, "rb") as file:
            response = client.files.create(file=file, purpose="vision")
            file_id = response.id

        # Delete the temporary file
        os.unlink(temp_file_path)

        # Add the file to the message
        message_content.append({
            "type": "image_file",
            "image_file": {"file_id": file_id}
        })

        # Store file info in session
        if 'files' not in session:
            session['files'] = []
        session['files'].append({'id': file_id, 'timestamp': datetime.now().isoformat()})
        session.modified = True

    # Create the message
    message = client.beta.threads.messages.create(
        thread_id=session['thread_id'],
        role="user",
        content=message_content,
    )

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=session['thread_id'],
        assistant_id=assistant_id,
    )

    run = wait_on_run(run, client.beta.threads.retrieve(session['thread_id']))

    # Retrieve the assistant's response
    messages = client.beta.threads.messages.list(
        thread_id=session['thread_id'], order="asc", after=message.id
    )

    # Clean the response
    raw_response = messages.data[0].content[0].text.value
    cleaned_response = clean_response(raw_response)

    return cleaned_response

def cleanup_files():
    if 'files' in session:
        current_time = datetime.now()
        files_to_keep = []
        for file in session['files']:
            file_time = datetime.fromisoformat(file['timestamp'])
            if current_time - file_time < FILE_TIMEOUT:
                files_to_keep.append(file)
            else:
                try:
                    client.files.delete(file['id'])
                except Exception as e:
                    print(f"Error deleting file {file['id']}: {e}")
        session['files'] = files_to_keep
        session.modified = True

app = Flask(__name__)
app.secret_key = 'b2e9c2e0f7ad4f91b5b84a2952d90b0c'

# Initialize OpenAI client with API key from secrets
api_key = os.getenv('OPENAI_API_KEY')
assistant_id = os.getenv('OPENAI_ASSISTANT_ID')

# Try to get credentials from secrets file if not in environment
secrets_path = '/etc/secrets/.env'
if os.path.exists(secrets_path):
    with open(secrets_path, 'r') as f:
        for line in f:
            if not api_key and line.startswith('OPENAI_API_KEY='):
                api_key = line.split('=')[1].strip()
            elif not assistant_id and line.startswith('OPENAI_ASSISTANT_ID='):
                assistant_id = line.split('=')[1].strip()

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment or secrets")
if not assistant_id:
    raise ValueError("OPENAI_ASSISTANT_ID not found in environment or secrets")

# Initialize OpenAI client with the API key
client = OpenAI(api_key=api_key)
FILE_TIMEOUT = timedelta(minutes=2)

def check_db_connection(f):
    @wraps(f)
    def decorated_function(restaurant_id, *args, **kwargs):
        try:
            mongo_service = MongoService.get_instance(restaurant_id)
            # Ping database to check connection
            mongo_service.client.admin.command('ping')
            return f(restaurant_id, *args, **kwargs)
        except Exception as e:
            return jsonify({
                "error": "Database connection error",
                "message": str(e)
            }), 503
    return decorated_function

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/select')
def select():
    # Show list of available restaurants
    return render_template('restaurant_select.html', restaurants=RESTAURANTS)

@app.route('/<restaurant_id>/')
def restaurant_index(restaurant_id):
    restaurant_config = get_restaurant_config(restaurant_id)
    if not restaurant_config:
        return "Restaurant not found", 404
    return render_template('index.html', restaurant=restaurant_config)

@app.route('/<restaurant_id>/api/tips/AddEntry', methods=['POST'])
def add_entry(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        data = request.json
        print(f"Received data: {data}")  # Debug log
        
        # Check if worker exists and add if new
        workers = mongo_service.get_workers()
        if data['name'] not in workers:
            workers_file = os.path.join(os.path.dirname(__file__), 'config', restaurant_id, 'workers.json')
            with open(workers_file, 'r', encoding='utf-8') as f:
                workers_data = json.load(f)
            
            workers_data['workers'].append(data['name'])
            workers_data['workers'].sort()  # Keep the list alphabetically sorted
            
            with open(workers_file, 'w', encoding='utf-8') as f:
                json.dump(workers_data, f, indent=4, ensure_ascii=False)
        
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

@app.route('/<restaurant_id>/api/tips/daily/<date>')
def get_daily_data(restaurant_id, date):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        restaurant_config = get_restaurant_config(restaurant_id)
        if not restaurant_config:
            return jsonify({"error": "Restaurant not found"}), 404

        date_obj = datetime.strptime(date, '%Y-%m-%d')
        day_of_week = date_obj.strftime('%A').lower()  # e.g., 'saturday'
        min_hourly_rate = restaurant_config['min_hourly_rate']

        if isinstance(min_hourly_rate, dict):
            MIN_HOURLY_RATE = min_hourly_rate.get(day_of_week, min_hourly_rate.get('default', 50))
        else:
            MIN_HOURLY_RATE = min_hourly_rate

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

@app.route('/<restaurant_id>/api/tips/monthly/<month>')
@check_db_connection
def get_monthly_data(restaurant_id, month):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        restaurant_config = get_restaurant_config(restaurant_id)
        if not restaurant_config:
            return jsonify({"error": "Restaurant not found"}), 404

        min_hourly_rate_config = restaurant_config['min_hourly_rate']
        start_date = datetime.strptime(f"{month}-01", '%Y-%m-%d')
        daily_entries = mongo_service.get_employees_for_month(start_date)
        
        # Group entries by date to handle daily tip pools
        daily_totals = {}
        for entry in daily_entries:
            date = entry["date"]
            if date not in daily_totals:
                daily_totals[date] = {
                    "totalHours": 0,
                    "totalCashTips": 0,
                    "totalCreditTips": 0,
                    "employees": []
                }
            daily_totals[date]["totalHours"] += entry["hours"]
            daily_totals[date]["totalCashTips"] += entry["cashTips"]
            daily_totals[date]["totalCreditTips"] += entry["creditTips"]
            daily_totals[date]["employees"].append(entry)

        # Calculate monthly totals per employee
        employee_totals = {}
        monthly_total_hours = 0
        monthly_total_cash = 0
        monthly_total_credit = 0
        monthly_total_compensation = 0

        # Calculate daily distributions and compensations
        for date, day_data in daily_totals.items():
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_of_week = date_obj.strftime('%A').lower()

            if isinstance(min_hourly_rate_config, dict):
                min_rate = min_hourly_rate_config.get(day_of_week, min_hourly_rate_config.get('default', 50))
            else:
                min_rate = min_hourly_rate_config

            # Use min_rate in calculations
            total_hours = day_data["totalHours"]
            total_cash = day_data["totalCashTips"]
            total_credit = day_data["totalCreditTips"]
            total_tips = total_cash + total_credit

            avg_tips_per_hour = total_tips / total_hours if total_hours > 0 else 0
            compensation_needed = max(0, min_rate - avg_tips_per_hour)
            daily_compensation = compensation_needed * total_hours

            monthly_total_hours += total_hours
            monthly_total_cash += total_cash
            monthly_total_credit += total_credit
            monthly_total_compensation += daily_compensation

            # Calculate each employee's share for this day
            for emp in day_data["employees"]:
                name = emp["name"]
                if name not in employee_totals:
                    employee_totals[name] = {
                        "name": name,
                        "hours": 0,
                        "cashTips": 0,
                        "creditTips": 0,
                        "compensation": 0
                    }
                
                employee_totals[name]["hours"] += emp["hours"]
                employee_totals[name]["cashTips"] += emp["cashTips"]
                employee_totals[name]["creditTips"] += emp["creditTips"]
                
                if total_hours > 0:
                    hours_fraction = emp["hours"] / total_hours
                    emp_tips_per_hour = (emp["cashTips"] + emp["creditTips"]) / emp["hours"] if emp["hours"] > 0 else 0
                    emp_compensation_needed = max(0, min_rate - emp_tips_per_hour)
                    employee_totals[name]["compensation"] += emp_compensation_needed * emp["hours"]

        # Convert to list and round values
        employee_list = []
        for emp in employee_totals.values():
            emp["hours"] = round(emp["hours"], 2)
            emp["cashTips"] = round(emp["cashTips"], 2)
            emp["creditTips"] = round(emp["creditTips"], 2)
            emp["compensation"] = round(emp["compensation"], 2)
            emp["totalTips"] = round(emp["cashTips"] + emp["creditTips"], 2)
            emp["finalTotal"] = round(emp["totalTips"] + emp["compensation"], 2)
            emp["avgHourly"] = round(emp["finalTotal"] / emp["hours"], 2) if emp["hours"] > 0 else 0
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
        
        return jsonify(monthly_data)
    except Exception as e:
        print(f"Error in monthly data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/workers')
def get_workers(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        workers = mongo_service.get_workers()
        return jsonify(workers)
    except Exception as e:
        print(f"Error loading workers: {str(e)}")
        return jsonify([]), 500

@app.route('/<restaurant_id>/api/workers/add', methods=['POST'])
def add_worker(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        data = request.json
        if not data or 'name' not in data:
            return jsonify({"error": "No name provided"}), 400

        new_name = data['name'].strip()
        if not new_name:
            return jsonify({"error": "Name cannot be empty"}), 400

        workers_file = os.path.join(os.path.dirname(__file__), 'config', restaurant_id, 'workers.json')
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

@app.route('/<restaurant_id>/api/tips/AddHours', methods=['POST'])
@check_db_connection
def add_hours(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        data = request.json
        print(f"Received hours data: {data}")  # Debug log
        
        # Check if worker exists and add if new
        workers = mongo_service.get_workers()
        if data['name'] not in workers:
            # Add new worker to MongoDB collection
            collection = mongo_service.db[mongo_service.get_collection_name('workers')]
            collection.update_one(
                {}, 
                {"$push": {"workers": data['name']}},
                upsert=True
            )
        
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
        
        with mongo_service.session_scope() as session:
            result = mongo_service.upsert_employee_hours(input_date, employee_data, session)
            return jsonify({"status": "success", "message": "Hours updated successfully"})
    except Exception as e:
        print(f"Error adding hours: {str(e)}")  # Debug log
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/<restaurant_id>/api/tips/AddTips', methods=['POST'])
def add_tips(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
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

@app.route('/<restaurant_id>/debug')
def debug_db(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        
        # Check collections
        workers_coll = mongo_service.get_collection_name('workers')
        daily_coll = mongo_service.get_collection_name('dailyEntries')
        
        # Get sample data
        workers = mongo_service.db[workers_coll].find_one({})
        daily = mongo_service.db[daily_coll].find_one({})
        
        debug_info = {
            "database": mongo_service.db.name,
            "collections": {
                "workers": {
                    "name": workers_coll,
                    "sample": workers
                },
                "dailyEntries": {
                    "name": daily_coll,
                    "sample": str(daily) if daily else None
                }
            }
        }
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/priority/')
def priority_home():
    return render_template('priority/index.html')

@app.route('/priority/chat', methods=['POST'])
def priority_chat():
    cleanup_files()
    user_message = request.form.get('message', '')
    image = request.files.get('image')
    image_data = image.read() if image else None
    response = get_assistant_response(user_message, image_data)
    return jsonify({'response': response})

@app.route('/priority/end_conversation', methods=['POST'])
def priority_end_conversation():
    if 'files' in session:
        for file in session['files']:
            try:
                client.files.delete(file['id'])
            except Exception as e:
                print(f"Error deleting file {file['id']}: {e}")
    session.clear()
    return jsonify({'message': 'Conversation ended and resources cleaned up.'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
