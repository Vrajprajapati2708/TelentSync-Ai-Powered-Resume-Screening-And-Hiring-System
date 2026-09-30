import urllib.request, json
try:
    resp = urllib.request.urlopen('http://127.0.0.1:5000/api/admin/stats')
    data = json.loads(resp.read().decode())
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")
