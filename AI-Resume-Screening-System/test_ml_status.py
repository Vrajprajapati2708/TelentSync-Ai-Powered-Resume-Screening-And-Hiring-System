import urllib.request, json
resp = urllib.request.urlopen('http://127.0.0.1:5000/api/ml/status')
data = json.loads(resp.read().decode())
print(json.dumps(data, indent=2))
