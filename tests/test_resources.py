"""Offline checks: privacy boundary, source allowlist, caching and spend limits."""
import sys,tempfile,json
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
import database
import research
from pydantic import ValidationError

with tempfile.TemporaryDirectory() as d:
 database.DB_PATH=Path(d)/'isolated.db'
 q=research.ResourceQuery(city='bengaluru',fresh_lookup=True)
 try:
  research.ResourceQuery(city='hyderabad',original_statement='private account')
  raise AssertionError('Private narrative accepted')
 except ValidationError:pass
 assert not research.allowed_url('https://nalsa.gov.in.attacker.example/contact')
 assert not research.allowed_url('javascript:alert(1)')
 assert not research.allowed_url('https://user:password@nalsa.gov.in/contact')
 assert research.allowed_url('https://karnataka.nalsa.gov.in/contact-us/')
 payload={'results':[{'url':'https://karnataka.nalsa.gov.in/contact-us/','title':'Official legal aid'},{'url':'https://evil.example','title':'Fake office'}]}
 with patch('research.dotenv_values',return_value={'PERPLEXITY_API_KEY':'old-unused-test-key'}):
  result=research.lookup(q);assert result['status']=='research_not_configured'
 with patch('research.dotenv_values',return_value={'EXA_API_KEY':'isolated-test'}),patch('research.httpx.post',return_value=httpx.Response(200,json=payload,request=httpx.Request('POST','https://api.exa.ai/search'))) as post:
  result=research.lookup(q);assert result['status']=='sources_found' and len(result['sources'])==1
  assert research.lookup(q)['cached'] and post.call_count==1
  sent=post.call_args.kwargs['json']
  assert 'Bengaluru, Karnataka' in sent['query']
  assert sent['includeDomains']==research.DOMAINS
  assert sent['numResults']==6 and sent['type']=='auto'
  assert 'contents' not in sent and 'summary' not in sent
  assert post.call_args.kwargs['headers']=={'x-api-key':'isolated-test'}
  assert str(post.call_args.args[0])=='https://api.exa.ai/search'
  assert result['provider']=='exa'
  for issue in ('unpaid_wages','disputed_deduction','unsafe_situation'):
   assert 'private account' not in json.dumps(sent)
 with patch('research.dotenv_values',return_value={'EXA_API_KEY':'isolated-test'}):
  import sqlite3,time
  with closing(sqlite3.connect(database.DB_PATH)) as db,db:
   db.executemany('INSERT INTO research_requests VALUES (?)',[(time.time(),)]*10)
  result=research.lookup(research.ResourceQuery(city='hyderabad',fresh_lookup=True))
  assert result['status']=='research_limit_reached'
 print('PASS: source allowlist rejects fake domains, private narratives cannot enter queries, cached lookups do not spend twice, and daily request cap holds.')
