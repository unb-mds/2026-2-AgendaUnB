"""Sondagem pública pequena; não publica catálogo nem comprova cobertura total."""
import json
from src.modules.classes.followw import FollowwClient, normalize

client = FollowwClient()
units = client.get('/public/classrooms/units')
live = client.get('/public/classrooms', code='FGA0108', semester='2026.2')
subjects = client.get('/public/subjects', code='FGA0108', semester='2026.2')
unit = next(u for u in units if u['id'] == 673)
rows, rejected = normalize(live, subjects, unit, '2026.2')
print(json.dumps({'units': len(units), 'period': '2026.2', 'code': 'FGA0108', 'live_offerings': len(live),
    'subjects': len(subjects), 'normalized': len(rows), 'rejected': len(rejected),
    'offering_ids_present': sum(r['oferta_origem_id'] is not None for r in rows)}, ensure_ascii=False))
