
import os
import json
from utils.logger import setup_logger

logger = setup_logger("config_check")

def check_sheets_configuration():
    """Comprehensive check of Google Sheets configuration."""
    
    print("🔍 GOOGLE SHEETS CONFIGURATION CHECK")
    print("=" * 50)
    
    issues = []
    
    # Check credentials
    creds_env = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    if creds_env:
        print("✅ GOOGLE_SHEETS_CREDENTIALS environment variable is set")
        try:
            creds_dict = json.loads(creds_env)
            required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
            missing_keys = [key for key in required_keys if key not in creds_dict]
            
            if missing_keys:
                print(f"❌ Missing required keys in credentials: {missing_keys}")
                issues.append("Invalid credentials format")
            else:
                print("✅ Credentials JSON format appears valid")
                
        except json.JSONDecodeError:
            print("❌ GOOGLE_SHEETS_CREDENTIALS is not valid JSON")
            issues.append("Invalid credentials JSON")
    else:
        print("❌ GOOGLE_SHEETS_CREDENTIALS environment variable not set")
        
        # Check for credentials file
        if os.path.exists('credentials.json'):
            print("✅ Found credentials.json file as fallback")
        else:
            print("❌ No credentials.json file found")
            issues.append("No credentials configured")
    
    # Check spreadsheet ID
    sheets_id = os.getenv('GOOGLE_SHEETS_ID')
    if sheets_id:
        print(f"✅ GOOGLE_SHEETS_ID is set: {sheets_id}")
    else:
        print("⚠️ GOOGLE_SHEETS_ID not set (will create new spreadsheet)")
    
    # Test connection
    try:
        from sheets import SheetsManager
        print("\n🔗 TESTING CONNECTION...")
        
        sheets = SheetsManager()
        if sheets.is_connected():
            print("✅ Successfully connected to Google Sheets!")
            if sheets.spreadsheet:
                print(f"📊 Spreadsheet URL: {sheets.spreadsheet.url}")
                
                # List worksheets
                try:
                    worksheets = [ws.title for ws in sheets.spreadsheet.worksheets()]
                    print(f"📋 Available worksheets: {', '.join(worksheets)}")
                except Exception as e:
                    print(f"⚠️ Could not list worksheets: {e}")
                    
        else:
            print("❌ Failed to connect to Google Sheets")
            status = sheets.get_connection_status()
            print(f"Connection status: {status}")
            issues.append("Connection failed")
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        issues.append(f"Connection test failed: {e}")
    
    # Summary
    print("\n📋 SUMMARY")
    print("=" * 20)
    
    if not issues:
        print("✅ All checks passed! Google Sheets integration should work.")
    else:
        print("❌ Issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Ensure you have a Google Service Account")
        print("2. Download the service account key (JSON file)")
        print("3. Set GOOGLE_SHEETS_CREDENTIALS with the JSON content")
        print("4. Optionally set GOOGLE_SHEETS_ID to reuse existing spreadsheet")
        print("5. Restart the bot after setting environment variables")

if __name__ == "__main__":
    check_sheets_configuration()
