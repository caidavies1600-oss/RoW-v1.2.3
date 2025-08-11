
#!/usr/bin/env python3
"""
Script to clear all JSON data files and reset them to default structures.
"""

import os
import json
import shutil
from datetime import datetime
from config.constants import FILES

def backup_existing_data():
    """Create backups of existing data files."""
    backup_dir = f"data/backups/clear_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    backed_up = []
    for file_path in FILES.values():
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            backed_up.append(os.path.basename(file_path))
    
    return backup_dir, backed_up

def get_default_structures():
    """Get default data structures for all JSON files."""
    return {
        FILES["EVENTS"]: {
            "main_team": [],
            "team_2": [],
            "team_3": []
        },
        FILES["BLOCKED"]: {},
        FILES["IGN_MAP"]: {},
        FILES["ABSENT"]: {},
        FILES["RESULTS"]: {
            "total_wins": 0,
            "total_losses": 0,
            "history": []
        },
        FILES["HISTORY"]: {
            "history": []
        },
        FILES["PLAYER_STATS"]: {},
        FILES["TIMES"]: {
            "main_team": "18:30 UTC Tuesday",
            "team_2": "18:30 UTC Tuesday", 
            "team_3": "18:30 UTC Tuesday"
        },
        FILES["SIGNUP_LOCK"]: False,
        FILES["NOTIFICATION_PREFS"]: {
            "users": {},
            "default_settings": {}
        },
        "data/match_statistics.json": {
            "matches": []
        }
    }

def clear_all_data():
    """Clear all JSON data files and reset to defaults."""
    print("🔄 Starting data clear operation...")
    
    # Create backup first
    print("📦 Creating backup of existing data...")
    backup_dir, backed_up = backup_existing_data()
    
    if backed_up:
        print(f"✅ Backed up {len(backed_up)} files to: {backup_dir}")
        for file in backed_up:
            print(f"   - {file}")
    else:
        print("ℹ️ No existing data files found to backup")
    
    # Get default structures
    defaults = get_default_structures()
    
    # Clear each file
    cleared = []
    failed = []
    
    for file_path, default_data in defaults.items():
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write default data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            
            cleared.append(os.path.basename(file_path))
            print(f"✅ Cleared: {os.path.basename(file_path)}")
            
        except Exception as e:
            failed.append(f"{os.path.basename(file_path)}: {e}")
            print(f"❌ Failed to clear {os.path.basename(file_path)}: {e}")
    
    # Summary
    print(f"\n📊 Data Clear Summary:")
    print(f"   ✅ Successfully cleared: {len(cleared)} files")
    if failed:
        print(f"   ❌ Failed to clear: {len(failed)} files")
        for failure in failed:
            print(f"      - {failure}")
    
    if backup_dir and backed_up:
        print(f"\n💾 Backup location: {backup_dir}")
        print("   You can restore from backup if needed")
    
    print(f"\n🎯 All JSON data has been reset to default structures!")
    print("   All teams are now empty")
    print("   All stats have been reset")
    print("   All user data has been cleared")

if __name__ == "__main__":
    try:
        clear_all_data()
    except Exception as e:
        print(f"💥 Critical error during data clear: {e}")
        import traceback
        traceback.print_exc()
