from flask import Flask, request, jsonify, render_template, session, redirect
from mongo_service import MongoService
from datetime import datetime
import json
import os
from restaurant_config import (
    get_restaurant_config, 
    get_all_restaurants,
    create_restaurant,
    update_restaurant
)
from init_restaurant import init_restaurant
from functools import wraps
import atexit
from openai import OpenAI
import time
import tempfile
import re
from datetime import datetime, timedelta
import calendar


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

def get_worker_wage(mongo_service, worker_name, base_rate, day_of_week, saturday_multiplier=None):
    """Helper function to get worker's wage rate"""
    # Check for worker-specific wage
    wages_collection = mongo_service.db[mongo_service.get_collection_name('worker_wages')]
    worker_wage = wages_collection.find_one({"worker_name": worker_name})
    
    if worker_wage and 'base_wage' in worker_wage:
        base_rate = worker_wage['base_wage']
    
    # Apply Saturday multiplier if applicable
    if day_of_week == 'saturday' and saturday_multiplier:
        return base_rate * saturday_multiplier
    
    return base_rate

def has_individual_wages(mongo_service):
    """Helper function to check if any individual wages exist"""
    wages_collection = mongo_service.db[mongo_service.get_collection_name('worker_wages')]
    return wages_collection.count_documents({}) > 0

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

def check_layout_access(f):
    @wraps(f)
    def decorated_function(restaurant_id, *args, **kwargs):
        restaurant_config = get_restaurant_config(restaurant_id)
        if not restaurant_config:
            return "Restaurant not found", 404
            
        # If layout is closed, only allow access to specific endpoints
        if restaurant_config.get('layout_type') == 'closed':
            # Allow all API endpoints first
            if request.path.startswith(f'/{restaurant_id}/api/'):
                return f(restaurant_id, *args, **kwargs)
                
            # List of allowed endpoints for closed layout
            allowed_endpoints = [
                'add_entry',
                'add_hours',
                'add_tips',
                'get_workers',
                'add_worker',
                'restaurant_index',
                'restaurant_bill',
                # Worker portal endpoints
                'worker_portal',
                'worker_login',
                'worker_logout',
                'get_current_shift',
                'clock_in',
                'clock_out',
                # API endpoints
                'get_daily_data',
                'get_monthly_data',
                'get_employees_for_date',
                'get_employees_for_month'
            ]
            
            # If not an allowed endpoint and not the bill page, redirect to bill
            if request.endpoint not in allowed_endpoints:
                return redirect(f'/{restaurant_id}/bill')
                
        return f(restaurant_id, *args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/supersuper')
def supersuper():
    return render_template('supersuper.html')

@app.route('/select')
def select():
    # Show list of available restaurants
    restaurants = get_all_restaurants()
    return render_template('restaurant_select.html', restaurants=restaurants)

@app.route('/create-restaurant', methods=['GET', 'POST'])
def create_restaurant_page():
    if request.method == 'POST':
        restaurant_id = request.form.get('restaurant_id')
        name = request.form.get('name')
        min_hourly_rate = request.form.get('min_hourly_rate')
        saturday_multiplier = request.form.get('saturday_multiplier')
        compensation_type = request.form.get('compensation_type')
        tips_threshold = request.form.get('tips_threshold')
        tips_type = request.form.get('tips_type')
        layout_type = request.form.get('layout_type', 'open')  # Default to 'open'
        
        config = {
            'name': name,
            'min_hourly_rate': float(min_hourly_rate) if not saturday_multiplier else {
                'default': float(min_hourly_rate),
                'saturday_multiplier': float(saturday_multiplier)
            },
            'compensation_type': compensation_type,
            'layout_type': layout_type  # Add layout_type to config
        }
        
        if tips_threshold:
            config['tips_threshold'] = float(tips_threshold)
        if tips_type:
            config['tips_type'] = tips_type
            
        try:
            create_restaurant(restaurant_id, config)
            # Initialize the restaurant's workers collection
            init_restaurant(restaurant_id)
            return redirect(f'/{restaurant_id}/admin')
        except Exception as e:
            return render_template('create_restaurant.html', error=str(e))
            
    return render_template('create_restaurant.html')

@app.route('/<restaurant_id>/admin', methods=['GET', 'POST'])
def admin_page(restaurant_id):
    restaurant_config = get_restaurant_config(restaurant_id)
    if not restaurant_config:
        return "Restaurant not found", 404
        
    mongo_service = MongoService.get_instance(restaurant_id)
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_config':
            min_hourly_rate = request.form.get('min_hourly_rate')
            saturday_multiplier = request.form.get('saturday_multiplier')
            compensation_type = request.form.get('compensation_type')
            tips_threshold = request.form.get('tips_threshold')
            tips_type = request.form.get('tips_type')
            layout_type = request.form.get('layout_type')
            
            config = restaurant_config.copy()
            config['min_hourly_rate'] = float(min_hourly_rate) if not saturday_multiplier else {
                'default': float(min_hourly_rate),
                'saturday_multiplier': float(saturday_multiplier)
            }
            config['compensation_type'] = compensation_type
            config['layout_type'] = layout_type
            
            if tips_threshold:
                config['tips_threshold'] = float(tips_threshold)
            if tips_type:
                config['tips_type'] = tips_type
                
            update_restaurant(restaurant_id, config)
            return redirect(f'/{restaurant_id}/admin')
            
        elif action == 'add_worker':
            worker_name = request.form.get('worker_name')
            if worker_name:
                collection = mongo_service.db[mongo_service.get_collection_name('workers')]
                collection.update_one(
                    {}, 
                    {"$addToSet": {"workers": worker_name}},
                    upsert=True
                )
                
        elif action == 'remove_worker':
            worker_name = request.form.get('worker_name')
            if worker_name:
                # Remove worker from workers list
                collection = mongo_service.db[mongo_service.get_collection_name('workers')]
                collection.update_one(
                    {}, 
                    {"$pull": {"workers": worker_name}}
                )
                
                # Remove worker's wage configuration if exists
                wages_collection = mongo_service.db[mongo_service.get_collection_name('worker_wages')]
                wages_collection.delete_one({"worker_name": worker_name})
                
        elif action == 'update_worker_wage':
            worker_name = request.form.get('worker_name')
            if worker_name:
                base_wage = request.form.get(f'base_wage_{worker_name}')
                tip_participation = request.form.get(f'tip_participation_{worker_name}') == 'on'
                
                wages_collection = mongo_service.db[mongo_service.get_collection_name('worker_wages')]
                if base_wage and float(base_wage) > 0:
                    # Update or insert worker's wage
                    wages_collection.update_one(
                        {"worker_name": worker_name},
                        {"$set": {
                            "worker_name": worker_name,
                            "base_wage": float(base_wage),
                            "tip_participation": tip_participation
                        }},
                        upsert=True
                    )
                else:
                    # If base_wage is empty or 0, remove custom wage but keep tip participation setting
                    if tip_participation:
                        wages_collection.update_one(
                            {"worker_name": worker_name},
                            {"$set": {
                                "worker_name": worker_name,
                                "tip_participation": tip_participation
                            }},
                            upsert=True
                        )
                    else:
                        wages_collection.delete_one({"worker_name": worker_name})
                
    # Get current workers and their wages
    workers = mongo_service.get_workers()
    
    # Get worker-specific wages
    wages_collection = mongo_service.db[mongo_service.get_collection_name('worker_wages')]
    worker_wages = {
        wage['worker_name']: wage 
        for wage in wages_collection.find({})
    }
    
    return render_template(
        'admin.html',
        restaurant=restaurant_config,
        restaurant_id=restaurant_id,
        workers=workers,
        worker_wages=worker_wages
    )

@app.route('/<restaurant_id>/')
@check_layout_access
def restaurant_index(restaurant_id):
    restaurant_config = get_restaurant_config(restaurant_id)
    if not restaurant_config:
        return "Restaurant not found", 404
        
    # Pass today's date to the template
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Use different template based on layout type
    template = 'index_closed.html' if restaurant_config.get('layout_type') == 'closed' else 'index.html'
    return render_template(template, restaurant=restaurant_config, today=today)

@app.route('/<restaurant_id>/bill')
def restaurant_bill(restaurant_id):
    restaurant_config = get_restaurant_config(restaurant_id)
    if not restaurant_config:
        return "Restaurant not found", 404
    
    # Only allow access to bill page if layout is closed
    if restaurant_config.get('layout_type') != 'closed':
        return redirect(f'/{restaurant_id}/')
    
    # Pass today's date to the template
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('bill.html', restaurant=restaurant_config, today=today)

@app.route('/<restaurant_id>/api/tips/AddEntry', methods=['POST'])
@check_layout_access
def add_entry(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        data = request.json
        print(f"Received data: {data}")  # Debug log
        
        # Check if worker exists and add if new
        workers = mongo_service.get_workers()
        if data['name'] not in workers:
            mongo_service = MongoService.get_instance(restaurant_id)
            collection = mongo_service.db[mongo_service.get_collection_name('workers')]
            collection.update_one(
                {}, 
                {"$addToSet": {"workers": data['name']}},
                upsert=True
            )
        
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
        day_of_week = date_obj.strftime('%A').lower()
        min_hourly_rate = restaurant_config['min_hourly_rate']
        compensation_type = restaurant_config.get('compensation_type', 'round_up')

        # Get base rate and Saturday multiplier
        if isinstance(min_hourly_rate, dict):
            base_rate = min_hourly_rate.get('default', 50)
            saturday_multiplier = min_hourly_rate.get('saturday_multiplier', 1.0)
        else:
            base_rate = min_hourly_rate
            saturday_multiplier = None

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

        # Calculate totals
        total_hours = sum(e["hours"] for e in employees)
        total_cash_tips = sum(e["cashTips"] for e in employees)
        total_credit_tips = sum(e["creditTips"] for e in employees)
        total_tips = total_cash_tips + total_credit_tips
        
        # Calculate daily average tips per hour
        avg_tips_per_hour = round(total_tips / total_hours, 2) if total_hours > 0 else 0

        # Check if we need to look up individual wages
        has_individual = has_individual_wages(mongo_service)

        total_compensation = 0
        # Calculate each employee's share and compensation
        for emp in employees:
            try:
                hours_fraction = emp["hours"] / total_hours if total_hours > 0 else 0
                emp["cashTips"] = round(total_cash_tips * hours_fraction, 2)
                emp["creditTips"] = round(total_credit_tips * hours_fraction, 2)
                emp["totalTips"] = round(emp["cashTips"] + emp["creditTips"], 2)
                
                # Get worker's wage rate - skip individual wage check if none exist
                if has_individual:
                    worker_rate = get_worker_wage(
                        mongo_service, 
                        emp["name"], 
                        base_rate, 
                        day_of_week, 
                        saturday_multiplier
                    )
                else:
                    # Use default rate with Saturday multiplier if applicable
                    worker_rate = base_rate * saturday_multiplier if day_of_week == 'saturday' and saturday_multiplier else base_rate

                # Special handling for Shapira
                if restaurant_id == 'shapira':
                    tips_threshold = restaurant_config.get('tips_threshold', 10)
                    tips_per_hour = emp["totalTips"] / emp["hours"] if emp["hours"] > 0 else 0
                    
                    if tips_per_hour < tips_threshold:
                        emp_compensation_needed = max(0, worker_rate - tips_per_hour)
                        emp["compensation"] = round(emp_compensation_needed * emp["hours"], 2)
                    else:
                        emp["compensation"] = round(30 * emp["hours"], 2)
                else:
                    if compensation_type == 'additive':
                        emp["compensation"] = round(worker_rate * emp["hours"], 2)
                    else:  # round_up
                        emp_tips_per_hour = emp["totalTips"] / emp["hours"] if emp["hours"] > 0 else 0
                        emp_compensation_needed = max(0, worker_rate - emp_tips_per_hour)
                        emp["compensation"] = round(emp_compensation_needed * emp["hours"], 2)
                
                emp["finalTotal"] = round(emp["totalTips"] + emp["compensation"], 2)
                emp["effectiveHourly"] = round((emp["finalTotal"] / emp["hours"]) if emp["hours"] > 0 else 0, 2)
                total_compensation += emp["compensation"]
            except Exception as emp_error:
                print(f"Error processing employee {emp.get('name', 'unknown')}: {str(emp_error)}")
                import traceback
                traceback.print_exc()
                raise Exception(f"Error processing employee {emp.get('name', 'unknown')}: {str(emp_error)}")

        daily_data = {
            "totalHours": round(total_hours, 2),
            "totalCashTips": round(total_cash_tips, 2),
            "totalCreditTips": round(total_credit_tips, 2),
            "totalTips": round(total_tips, 2),
            "avgTipsPerHour": avg_tips_per_hour,
            "compensation": round(total_compensation, 2),
            "employees": employees
        }
        
        return jsonify(daily_data)
    except Exception as e:
        print(f"Error in daily data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/tips/monthly/<month>')
@check_db_connection
def get_monthly_data(restaurant_id, month):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        restaurant_config = get_restaurant_config(restaurant_id)
        if not restaurant_config:
            return jsonify({"error": "Restaurant not found"}), 404

        # Get configuration
        min_hourly_rate = restaurant_config['min_hourly_rate']
        compensation_type = restaurant_config.get('compensation_type', 'round_up')
        
        # Get base rate and Saturday multiplier
        if isinstance(min_hourly_rate, dict):
            base_rate = min_hourly_rate.get('default', 50)
            saturday_multiplier = min_hourly_rate.get('saturday_multiplier', 1.0)
            has_saturday_rate = True
        else:
            base_rate = min_hourly_rate
            saturday_multiplier = None
            has_saturday_rate = False

        # Get monthly entries
        start_date = datetime.strptime(f"{month}-01", '%Y-%m-%d')
        daily_entries = mongo_service.get_employees_for_month(start_date)

        # Initialize tracking variables
        employee_totals = {}
        monthly_total_hours = 0
        monthly_total_cash = 0
        monthly_total_credit = 0
        monthly_total_compensation = 0

        # Check if we need to look up individual wages
        has_individual = has_individual_wages(mongo_service)

        # Group entries by date
        daily_totals = {}
        for entry in daily_entries:
            date_key = entry["date"].strftime('%Y-%m-%d')
            if date_key not in daily_totals:
                daily_totals[date_key] = {
                    "date": entry["date"],
                    "totalHours": 0,
                    "totalCashTips": 0,
                    "totalCreditTips": 0,
                    "employees": []
                }
            
            daily_totals[date_key]["totalHours"] += entry["hours"]
            daily_totals[date_key]["totalCashTips"] += entry.get("cashTips", 0)
            daily_totals[date_key]["totalCreditTips"] += entry.get("creditTips", 0)
            daily_totals[date_key]["employees"].append(entry)

        # Process each day
        for date_key, day_data in daily_totals.items():
            day_of_week = day_data["date"].strftime('%A').lower()
            total_hours = day_data["totalHours"]
            total_cash = day_data["totalCashTips"]
            total_credit = day_data["totalCreditTips"]
            total_tips = total_cash + total_credit

            # Update monthly totals
            monthly_total_hours += total_hours
            monthly_total_cash += total_cash
            monthly_total_credit += total_credit

            # Calculate daily tips per hour
            daily_tips_per_hour = total_tips / total_hours if total_hours > 0 else 0

            # Process each employee's data for this day
            for emp in day_data["employees"]:
                name = emp["name"]
                if name not in employee_totals:
                    employee_totals[name] = {
                        "name": name,
                        "hours": 0,
                        "cashTips": 0,
                        "creditTips": 0,
                        "compensation": 0,
                        "saturday_hours": 0
                    }

                # Calculate employee's share of tips
                emp_hours_fraction = emp["hours"] / total_hours if total_hours > 0 else 0
                emp_cash = total_cash * emp_hours_fraction
                emp_credit = total_credit * emp_hours_fraction

                # Get worker's wage rate - skip individual wage check if none exist
                if has_individual:
                    worker_rate = get_worker_wage(
                        mongo_service,
                        name,
                        base_rate,
                        day_of_week,
                        saturday_multiplier
                    )
                else:
                    # Use default rate with Saturday multiplier if applicable
                    worker_rate = base_rate * saturday_multiplier if day_of_week == 'saturday' and saturday_multiplier else base_rate

                # Calculate compensation
                if restaurant_id == 'shapira':
                    tips_threshold = restaurant_config.get('tips_threshold', 10)
                    emp_tips_per_hour = (emp_cash + emp_credit) / emp["hours"] if emp["hours"] > 0 else 0
                    
                    if emp_tips_per_hour < tips_threshold:
                        emp_compensation = max(0, worker_rate - emp_tips_per_hour) * emp["hours"]
                    else:
                        emp_compensation = 30 * emp["hours"]
                else:
                    if compensation_type == 'additive':
                        emp_compensation = worker_rate * emp["hours"]
                    else:  # round_up
                        emp_tips_per_hour = (emp_cash + emp_credit) / emp["hours"] if emp["hours"] > 0 else 0
                        emp_compensation = max(0, worker_rate - emp_tips_per_hour) * emp["hours"]

                # Update employee totals
                employee_totals[name]["hours"] += emp["hours"]
                employee_totals[name]["cashTips"] += emp_cash
                employee_totals[name]["creditTips"] += emp_credit
                employee_totals[name]["compensation"] += emp_compensation
                
                if day_of_week == 'saturday':
                    employee_totals[name]["saturday_hours"] += emp["hours"]

                monthly_total_compensation += emp_compensation

        # Format employee totals
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

        # Sort by final total
        employee_list.sort(key=lambda x: x["finalTotal"], reverse=True)

        return jsonify({
            "totalHours": round(monthly_total_hours, 2),
            "totalCashTips": round(monthly_total_cash, 2),
            "totalCreditTips": round(monthly_total_credit, 2),
            "totalCompensation": round(monthly_total_compensation, 2),
            "employeeTotals": employee_list,
            "has_saturday_rate": has_saturday_rate
        })

    except Exception as e:
        print(f"Error in monthly data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/workers')
@check_layout_access
def get_workers(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        workers = mongo_service.get_workers()
        return jsonify(workers)
    except Exception as e:
        print(f"Error loading workers: {str(e)}")
        return jsonify([]), 500

@app.route('/<restaurant_id>/api/workers/add', methods=['POST'])
@check_layout_access
def add_worker(restaurant_id):
    try:
        mongo_service = MongoService.get_instance(restaurant_id)
        data = request.json
        if not data or 'name' not in data:
            return jsonify({"error": "No name provided"}), 400

        new_name = data['name'].strip()
        if not new_name:
            return jsonify({"error": "Name cannot be empty"}), 400

        collection = mongo_service.db[mongo_service.get_collection_name('workers')]
        collection.update_one(
            {}, 
            {"$addToSet": {"workers": new_name}},
            upsert=True
        )

        # Get updated list of workers
        workers = mongo_service.get_workers()
        return jsonify({"message": "Worker added successfully", "workers": workers})
    except Exception as e:
        print(f"Error adding worker: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/tips/AddHours', methods=['POST'])
@check_layout_access
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
@check_layout_access
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

@app.route('/<restaurant_id>/worker-portal')
def worker_portal(restaurant_id):
    restaurant_config = get_restaurant_config(restaurant_id)
    if not restaurant_config:
        return "Restaurant not found", 404
    return render_template('worker_portal.html', 
                         restaurant=restaurant_config,
                         js_file='worker_portal.js')

@app.route('/<restaurant_id>/api/worker/login', methods=['POST'])
@check_layout_access
def worker_login(restaurant_id):
    try:
        data = request.json
        if not data or 'name' not in data:
            return jsonify({"error": "No name provided"}), 400
            
        session['worker_name'] = data['name']
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/worker/logout', methods=['POST'])
@check_layout_access
def worker_logout(restaurant_id):
    session.pop('worker_name', None)
    return jsonify({"status": "success"})

@app.route('/<restaurant_id>/api/worker/current-shift')
@check_layout_access
def get_current_shift(restaurant_id):
    try:
        if 'worker_name' not in session:
            return jsonify({"active_shift": False})
            
        mongo_service = MongoService.get_instance(restaurant_id)
        shift = mongo_service.get_active_shift(session['worker_name'])
        
        return jsonify({
            "active_shift": bool(shift),
            "start_time": shift['start_time'].isoformat() if shift else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/worker/clock-in', methods=['POST'])
@check_layout_access
def clock_in(restaurant_id):
    try:
        if 'worker_name' not in session:
            return jsonify({"error": "Not logged in"}), 401
            
        mongo_service = MongoService.get_instance(restaurant_id)
        mongo_service.start_shift(session['worker_name'])
        return jsonify({"status": "success"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/worker/clock-out', methods=['POST'])
@check_layout_access
def clock_out(restaurant_id):
    try:
        if 'worker_name' not in session:
            print(f"Clock-out attempt without worker_name in session")
            return jsonify({"error": "Not logged in"}), 401
            
        worker_name = session['worker_name']
        print(f"Attempting clock-out for {worker_name}")
            
        mongo_service = MongoService.get_instance(restaurant_id)
        # Get active shift first to check duration
        active_shift = mongo_service.get_active_shift(worker_name)
        if not active_shift:
            return jsonify({"error": "No active shift found"}), 400
            
        # Calculate duration before ending shift
        duration = datetime.now() - active_shift['start_time']
        if duration.total_seconds() < 60:  # Less than 1 minute
            return jsonify({"error": "Shift duration too short (less than 1 minute)"}), 400
            
        # Proceed with ending shift if duration is valid
        mongo_service.end_shift(worker_name)
        print(f"Successfully clocked out {worker_name}")
        return jsonify({"status": "success"})
    except ValueError as e:
        print(f"ValueError in clock-out for {worker_name}: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error in clock-out for {worker_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/<restaurant_id>/api/tips/allocation')
@check_layout_access
@check_db_connection
def get_tips_allocation(restaurant_id):
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({"error": "Date parameter is required"}), 400
            
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        
        mongo_service = MongoService.get_instance(restaurant_id)
        restaurant_config = get_restaurant_config(restaurant_id)
        if not restaurant_config:
            return jsonify({"error": "Restaurant not found"}), 404

        # Get employees who worked on this date
        employees = mongo_service.get_employees_for_date(date_obj)
        if not employees:
            return jsonify({
                "workers": [],
                "totalHours": 0,
                "totalCashTips": 0
            })

        # Calculate totals
        total_hours = sum(e["hours"] for e in employees)
        total_cash_tips = sum(e.get("cashTips", 0) for e in employees)

        # Calculate each worker's share based on hours
        workers_data = []
        for emp in employees:
            hours_fraction = emp["hours"] / total_hours if total_hours > 0 else 0
            cash_share = round(total_cash_tips * hours_fraction, 2)
            
            workers_data.append({
                "name": emp["name"],
                "hours": round(emp["hours"], 2),
                "cashTipsShare": cash_share
            })

        return jsonify({
            "workers": workers_data,
            "totalHours": round(total_hours, 2),
            "totalCashTips": round(total_cash_tips, 2)
        })

    except Exception as e:
        print(f"Error in tips allocation: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
