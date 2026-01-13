import requests
import os
import json
from datetime import datetime, timedelta

# Configuration
REPO = os.environ.get("GITHUB_REPOSITORY") # e.g., "username/repo"
TOKEN = os.environ.get("TRAFFIC_TOKEN") # Needs to be a PAT with repo scope
START_DATE = os.environ.get("START_DATE") # Optional: YYYY-MM-DD to start tracking from
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
        # Filter by START_DATE if set (format YYYY-MM-DD)
        if START_DATE and entry['timestamp'][:10] < START_DATE:
            continue
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
        
        # Fetch repo details for Stars and Forks
        repo_response = requests.get(f"https://api.github.com/repos/{REPO}", headers={"Authorization": f"token {TOKEN}"})
        repo_response.raise_for_status()
        repo_data = repo_response.json()

        # Fetch referrers
        ref_response = requests.get(f"https://api.github.com/repos/{REPO}/traffic/popular/referrers", headers={"Authorization": f"token {TOKEN}"})
        ref_response.raise_for_status()
        ref_data = ref_response.json()
        
        # 3. Merge
        db["views"] = merge_data(db, views_data, "views")
        db["clones"] = merge_data(db, clones_data, "clones")
        
        # 3b. Update Stars and Forks (Snapshot for today)
        today = datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")
        for metric, api_key in [("stars", "stargazers_count"), ("forks", "forks_count")]:
            if metric not in db: db[metric] = []
            # Remove entry if it exists for today (to allow re-runs) and append new
            db[metric] = [x for x in db[metric] if x['timestamp'] != today]
            db[metric].append({"timestamp": today, "count": repo_data.get(api_key, 0)})
            db[metric].sort(key=lambda x: x['timestamp'])

        # 3c. Update Referrers (Snapshot for today)
        if "referrers" not in db: db["referrers"] = []
        db["referrers"] = [x for x in db["referrers"] if x['timestamp'] != today]
        db["referrers"].append({"timestamp": today, "data": ref_data})
        db["referrers"].sort(key=lambda x: x['timestamp'])
        
        # 4. Cleanup old data (older than 1 year)
        one_year_ago = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z")
        for key in ["views", "clones", "stars", "forks", "referrers"]:
            if key in db:
                db[key] = [x for x in db[key] if x['timestamp'] >= one_year_ago]

        # 5. Add updated_at timestamp
        db["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # 6. Save
        with open(DATA_FILE, 'w') as f:
            json.dump(db, f, indent=2)
            
        print("Traffic data updated successfully.")
        
    except Exception as e:
        print(f"Error updating traffic: {e}")
        exit(1)

if __name__ == "__main__":
    main()
