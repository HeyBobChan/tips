from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1KRO-j3-bwekz01M80MgpM-xK51-pwtON7W-f2hIY4Oc'

class GoogleSheetsService:
    def __init__(self):
        credentials = Credentials.from_service_account_file(
            os.path.join(os.path.dirname(__file__), 'config', 'credentials.json'),
            scopes=SCOPES
        )
        self.service = build('sheets', 'v4', credentials=credentials)
        self.sheets = self.service.spreadsheets()

    def append_entry(self, values):
        date = datetime.strptime(values[0], '%d/%m/%Y')
        sheet_name = f"{date.strftime('%m-%Y')}"
        
        # Ensure the sheet exists before appending
        if not self.ensure_sheet_exists(sheet_name):
            raise Exception(f"Failed to create or verify sheet {sheet_name}")
        
        body = {
            'values': [values]
        }
        
        result = self.sheets.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A:F",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return result

    def get_employees_for_date(self, date):
        sheet_name = date.strftime('%m-%Y')
        date_str = date.strftime('%d/%m/%Y')
        
        result = self.sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A:F"
        ).execute()
        
        rows = result.get('values', [])
        employees = []
        
        for row in rows:
            if len(row) >= 6 and row[0] == date_str:
                employees.append({
                    "name": row[1],
                    "hours": float(row[3]),
                    "cashTips": float(row[4]),
                    "creditTips": float(row[5])
                })
        
        return employees

    def get_employees_for_month(self, start_date):
        sheet_name = start_date.strftime('%m-%Y')
        
        result = self.sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A:F"
        ).execute()
        
        rows = result.get('values', [])
        employees = []
        
        for row in rows[1:]:  # Skip header row
            if len(row) >= 6:
                try:
                    employees.append({
                        "name": row[1],
                        "hours": float(row[3]),
                        "cashTips": float(row[4]),
                        "creditTips": float(row[5])
                    })
                except (ValueError, IndexError):
                    continue
        
        return employees