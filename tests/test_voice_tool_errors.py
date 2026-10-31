import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SESSION_COOKIE_SECURE']='false'
from fastapi.testclient import TestClient
from bridge_app import app
from prepare_bolna_handoff import conversation_schema,inline_schema
from voice_backend import CalculateTool,IntakeTool

for name,model in [('calculate_reported_balance',CalculateTool),('prepare_case',IntakeTool)]:
    schema=conversation_schema(name,inline_schema(model.model_json_schema()))
    assert set(schema['required'])==set(schema['properties'])
    assert {'units_worked','rate_per_unit','voice_token','pay_basis'}<=set(schema['required'])
    assert not {'daily_rate','days_worked','reconstruction','adjustments_checked'}&set(schema['properties'])
    assert schema['properties']['units_worked']['type']=='integer'
    assert 'monthly' in schema['properties']['pay_basis']['enum']
    assert 'Never ask' in schema['properties']['voice_token']['description']

a=TestClient(app)
with patch('voice_backend.dotenv_values',return_value={'HAQRECORD_VOICE_TOOL_SECRET':'fictional-service-secret'}):
    headers={'Authorization':'Bearer fictional-service-secret'}
    body={'voice_token':'fictional-private-call-token-do-not-expose','pay_basis':'monthly','units_worked':'not-a-number','rate_per_unit':'3000','payments_received':'3000','adjustments_clear':True,'original_statement':'Fictional worker account.'}
    r=a.post('/bolna/tools/calculate',json=body,headers=headers)
    assert r.status_code==422 and r.json()['status']=='not_updated',r.text
    assert r.json()['on_screen'] is False and r.json()['saved'] is False
    assert r.json()['invalid_fields']==['units_worked']
    assert body['voice_token'] not in r.text and 'fictional-service-secret' not in r.text
    assert 'backend' not in r.json()['spoken_response'].lower()
    body['voice_token']='short'
    r=a.post('/bolna/tools/calculate',json=body,headers=headers)
    assert 'reconnect' in r.json()['spoken_response'].lower()
    assert 'token' not in r.json()['spoken_response'].lower()
print('PASS: voice cards require core facts and omit legacy fields; errors reveal no submitted values, never claim an update, and give natural speech instructions.')
