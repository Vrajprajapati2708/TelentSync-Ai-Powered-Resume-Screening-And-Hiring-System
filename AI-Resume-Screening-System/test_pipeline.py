"""Quick test of the ML pipeline API endpoint."""
import urllib.request, urllib.error, json

skills = ['Python', 'Machine Learning', 'SQL', 'Pandas', 'Scikit-Learn', 'NLP']
req = urllib.request.Request(
    'http://127.0.0.1:5000/api/match_jobs',
    data=json.dumps({'skills': skills}).encode(),
    headers={'Content-Type': 'application/json'}
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print('Success:', data['success'])
    print('Jobs returned:', len(data['jobs']))
    for j in data['jobs'][:5]:
        print(f"  {j['title']:20s}  match={j['match_percentage']}%  semantic={j.get('semantic_score',0):.3f}  skill={j.get('skill_score',0):.3f}")
except urllib.error.HTTPError as e:
    body = e.read().decode(errors='replace')
    # Extract the plaintext traceback
    if 'Traceback' in body:
        idx = body.rfind('Traceback')
        print(body[idx:])
    else:
        print(f'HTTP {e.code}')
        print(body[:500])
