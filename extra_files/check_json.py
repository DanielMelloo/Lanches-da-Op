import json
try:
    with open('/tmp/db.json') as f:
        data = json.load(f)
        print("--- STORES ---")
        for s in data['stores']:
            print(f"ID: {s['id']} | Subsite: {s['subsite_id']} | Name: {s['name']}")
        print("--- ADMINS ---")
        for u in data['users']:
            # Relaxed check for role
            role = str(u.get('role', ''))
            if 'admin' in role:
                print(f"ID: {u['id']} | Subsite: {u['subsite_id']} | Email: {u['email']}")
except Exception as e:
    print(f"Error: {e}")
