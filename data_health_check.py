#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from mongo_service import MongoService
from collections import defaultdict

def load_environment():
    load_dotenv()
    return {
        'uri': os.getenv('MONGODB_URI'),
        'db_name': os.getenv('MONGODB_DB_NAME')
    }

class DataHealthChecker:
    def __init__(self, restaurant_id):
        self.config = load_environment()
        self.mongo_service = MongoService.get_instance(restaurant_id)
        self.restaurant_id = restaurant_id
        self.issues = []

    def add_issue(self, category, description, severity="WARNING"):
        self.issues.append({
            "category": category,
            "description": description,
            "severity": severity
        })

    def check_general_database_health(self):
        """Check basic database connectivity and collection existence"""
        try:
            # Check if collections exist
            collections = self.mongo_service.db.list_collection_names()
            expected_collections = [
                f"{self.restaurant_id}_dailyEntries",
                f"{self.restaurant_id}_workers"
            ]
            
            for coll in expected_collections:
                if coll not in collections:
                    self.add_issue("Missing Collection", 
                                 f"Collection {coll} does not exist",
                                 "ERROR")
        except Exception as e:
            self.add_issue("Database Connection", 
                          f"Failed to connect to database: {str(e)}", 
                          "CRITICAL")

    def check_data_consistency(self):
        """Check for data consistency issues"""
        daily_entries = self.mongo_service.db[f"{self.restaurant_id}_dailyEntries"].find()
        
        for entry in daily_entries:
            # Check if required fields exist
            required_fields = ['date', 'employees', 'totalHours', 'totalCashTips', 'totalCreditTips']
            for field in required_fields:
                if field not in entry:
                    self.add_issue("Missing Field", 
                                 f"Entry {entry['_id']} is missing required field: {field}")
            
            if 'employees' in entry and entry['employees']:
                # Check employee data consistency
                total_hours = sum(emp.get('hours', 0) for emp in entry['employees'])
                if abs(total_hours - entry.get('totalHours', 0)) > 0.01:
                    self.add_issue("Data Mismatch", 
                                 f"Total hours mismatch for date {entry['date']}")
                
                # Check for employee data completeness
                for emp in entry['employees']:
                    required_emp_fields = ['name', 'hours', 'cashTips', 'creditTips']
                    for field in required_emp_fields:
                        if field not in emp:
                            self.add_issue("Missing Employee Data", 
                                         f"Employee record missing {field} for date {entry['date']}")

    def check_worker_list(self):
        """Check worker list integrity"""
        workers_coll = self.mongo_service.db[f"{self.restaurant_id}_workers"]
        workers_doc = workers_coll.find_one({})
        
        if not workers_doc or 'workers' not in workers_doc:
            self.add_issue("Missing Workers", "No workers list found", "ERROR")
            return
        
        # Get all unique worker names from daily entries
        daily_entries = self.mongo_service.db[f"{self.restaurant_id}_dailyEntries"].find()
        active_workers = set()
        for entry in daily_entries:
            if 'employees' in entry:
                for emp in entry['employees']:
                    if 'name' in emp:
                        active_workers.add(emp['name'])
        
        # Check for workers in entries but not in worker list
        registered_workers = set(workers_doc['workers'])
        unregistered_workers = active_workers - registered_workers
        if unregistered_workers:
            self.add_issue("Unregistered Workers", 
                          f"Workers in entries but not in worker list: {unregistered_workers}")

    def check_duplicates(self):
        """Check for duplicate entries"""
        daily_entries = self.mongo_service.db[f"{self.restaurant_id}_dailyEntries"].find()
        date_employee_map = defaultdict(list)
        
        for entry in daily_entries:
            if 'employees' in entry and entry['employees']:
                date = entry['date']
                for emp in entry['employees']:
                    if 'name' in emp:
                        date_employee_map[date].append(emp['name'])
        
        # Check for duplicate employee entries on the same date
        for date, employees in date_employee_map.items():
            duplicates = [emp for emp in employees if employees.count(emp) > 1]
            if duplicates:
                self.add_issue("Duplicate Entries", 
                             f"Duplicate employee entries found for date {date}: {set(duplicates)}")

    def run_health_check(self):
        """Run all health checks"""
        print(f"Starting health check for restaurant {self.restaurant_id}...")
        
        self.check_general_database_health()
        self.check_data_consistency()
        self.check_worker_list()
        self.check_duplicates()
        
        return self.generate_report()

    def generate_report(self):
        """Generate a formatted report of all issues"""
        report = f"\nHealth Check Report for Restaurant {self.restaurant_id}\n"
        report += "=" * 50 + "\n\n"
        
        if not self.issues:
            report += "✅ No issues found. All data appears to be healthy.\n"
            return report
        
        # Group issues by severity
        severity_groups = defaultdict(list)
        for issue in self.issues:
            severity_groups[issue['severity']].append(issue)
        
        # Report critical issues first
        for severity in ['CRITICAL', 'ERROR', 'WARNING']:
            if severity in severity_groups:
                report += f"\n{severity} Issues:\n"
                report += "-" * 20 + "\n"
                for issue in severity_groups[severity]:
                    report += f"• {issue['category']}: {issue['description']}\n"
        
        return report

if __name__ == "__main__":
    # You need to specify your restaurant_id here
    restaurant_id = input("Enter restaurant ID to check: ")
    checker = DataHealthChecker(restaurant_id)
    report = checker.run_health_check()
    print(report)
