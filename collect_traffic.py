import requests
import os
import json
from datetime import datetime

# Configuration
REPO = os.environ.get("GITHUB_REPOSITORY") # e.g., "username/repo"
TOKEN = os.environ.get("TRAFFIC_TOKEN") # Needs to be a PAT with repo scope
DATA_FILE = "traffic_data.json"

def get_traffic_data(metric):
    """Fetch views or clones from GitHub API"""
    url = f"https://api.github.com/repos/{REPO}/traffic/{metric}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def merge_data(existing, new_data, key):
    """Merge new API data with historical JSON data based on timestamp"""
    # Convert existing list to a dict for easy lookup by timestamp
    data_map = {entry['timestamp']: entry for entry in existing.get(key, [])}
    
    # Update or add new entries
    for entry in new_data.get(key, []):
        # The API returns timestamps like "2023-10-27T00:00:00Z"
        data_map[entry['timestamp']] = {
            "timestamp": entry['timestamp'],
            "count": entry['count'],
            "uniques": entry['uniques']
        }
    
    # Sort by timestamp and return list
    return sorted(data_map.values(), key=lambda x: x['timestamp'])

def main():
    print(f"Fetching traffic for {REPO}...")
    
    # 1. Load existing data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                db = json.load(f)
            except json.JSONDecodeError:
                db = {"views": [], "clones": []}
    else:
        db = {"views": [], "clones": []}

    # 2. Fetch new data
    try:
        views_data = get_traffic_data("views")
        clones_data = get_traffic_data("clones")
        
        # 3. Merge
        db["views"] = merge_data(db, views_data, "views")
        db["clones"] = merge_data(db, clones_data, "clones")
        
        # 4. Save
        with open(DATA_FILE, 'w') as f:
            json.dump(db, f, indent=2)
            
        print("Traffic data updated successfully.")
        
    except Exception as e:
        print(f"Error updating traffic: {e}")
        exit(1)

if __name__ == "__main__":
    main()
