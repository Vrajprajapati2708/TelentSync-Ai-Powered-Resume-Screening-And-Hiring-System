import urllib.request, json

if __name__ == "__main__":
    try:
        resp = urllib.request.urlopen('http://127.0.0.1:5000/api/ml/status')
        data = json.loads(resp.read().decode())
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Status check result: {e}")

