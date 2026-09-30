import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:5000/api/match_jobs', data=json.dumps({"skills":["Python","React"]}).encode(), headers={'Content-Type':'application/json'})
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print(json.dumps(data, indent=2)[:500] + '...')
except Exception as e:
    print(e)
