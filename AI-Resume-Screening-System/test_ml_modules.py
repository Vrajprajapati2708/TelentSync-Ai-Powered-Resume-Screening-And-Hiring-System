import sys
sys.path.insert(0, '.')

from app.ml.outlier.outlier_detector import detect_outliers
from app.ml.clustering.candidate_clusterer import cluster_candidates, get_cluster_groups

test_candidates = [
    {'name': 'Rahul',   'ats_score': 78, 'skills': 'Python,ML,TensorFlow,pandas'},
    {'name': 'Priya',   'ats_score':  3, 'skills': 'Word,Excel'},
    {'name': 'Ankit',   'ats_score': 65, 'skills': 'React,CSS,JavaScript,HTML'},
    {'name': 'Spammer', 'ats_score': 98, 'skills': 'Python,Java,React,DevOps,ML,AI,AWS'},
    {'name': 'Neha',    'ats_score': 72, 'skills': 'Docker,Kubernetes,AWS,Terraform'},
    {'name': 'Kiran',   'ats_score': 81, 'skills': 'Java,Spring,Hibernate,MySQL'},
]

result = detect_outliers(test_candidates)
result = cluster_candidates(result, n_clusters=4)
groups = get_cluster_groups(result)

print('== OUTLIER RESULTS ==')
for c in result:
    flag = 'FLAGGED' if c['outlier_flag'] else 'OK'
    name  = c['name']
    score = c['ats_score']
    label = c['cluster_label'].encode('ascii', 'ignore').decode()
    reason = c.get('outlier_reason', '').encode('ascii', 'ignore').decode()
    print(f'  {name:<10} | Score:{score:3d} | {flag:<7} | {label}')
    if reason:
        print(f'             > {reason}')

print()
print('== CLUSTER GROUPS ==')
for label, members in groups.items():
    names = [m['name'] for m in members]
    label_clean = label.encode('ascii', 'ignore').decode()
    print(f'  {label_clean}: {names}')
