"""Source discovery only: never sends case narrative or private worker data."""
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

import database
import worker
from next_steps import resource_action_card

router=APIRouter(prefix='/resources',tags=['Official resources'])
ROOT=Path(__file__).resolve().parent
CITIES={'hyderabad':('Hyderabad','Telangana'),'bengaluru':('Bengaluru','Karnataka')}
DOMAINS=['telangana.gov.in','karnataka.gov.in','labour.gov.in','clc.gov.in','nalsa.gov.in']
DIRECTORY={
 'hyderabad':[{'title':'Telangana Labour Department — official department and contacts',
 'url':'https://www.telangana.gov.in/departments/labour-employment-training-and-factories/',
 'checked_on':'2026-10-25','kind':'official_directory'}],
 'bengaluru':[{'title':'Karnataka State Legal Services Authority — official contact information','url':'https://karnataka.nalsa.gov.in/contact-us/','checked_on':'2026-10-25','kind':'official_directory'}]
}

class ResourceQuery(BaseModel):
    model_config=ConfigDict(extra='forbid')
    city:Literal['hyderabad','bengaluru']
    issue:Literal['unpaid_wages','disputed_deduction','unsafe_situation']='unpaid_wages'
    language:Literal['hi','en']='hi'
    fresh_lookup:bool=False

def allowed_url(url):
    try:
        p=urlsplit(url)
        return p.scheme=='https' and not p.username and not p.password and p.port in (None,443) and any(
            p.hostname==d or (p.hostname or '').endswith('.'+d) for d in DOMAINS)
    except (ValueError,TypeError):return False

def extract_sources(payload):
    """Keep source URLs, not unsourced model prose or invented phone numbers."""
    found={}
    results=payload.get('results',[]) if isinstance(payload,dict) else []
    if not isinstance(results,list):return []
    for item in results:
        if not isinstance(item,dict):continue
        url=item.get('url')
        if isinstance(url,str) and allowed_url(url) and len(url)<=2048:
            found[url]={'url':url,'title':str(item.get('title') or urlsplit(url).hostname)[:200],
                'kind':'research_source','checked_on':time.strftime('%Y-%m-%d',time.gmtime())}
    return list(found.values())[:6]


def lookup(data):
    config=dotenv_values(ROOT/'.env')
    directory=DIRECTORY[data.city]
    base={'provider':'exa','city':data.city,'issue':data.issue,'directory':directory,'sources':[],
          'action_card':resource_action_card(data.city,data.language),
          'jurisdiction_verified':False,'complaint_submitted':False,
          'notice':'Official source links only. Confirm jurisdiction and current requirements with the authority. No outcome or deadline is guaranteed.'}
    if not data.fresh_lookup:
        return {**base,'status':'directory' if directory else 'lookup_required'}
    key=config.get('EXA_API_KEY')
    if not key:return {**base,'status':'research_not_configured'}
    cache_key='exa:v1:'+data.city+':'+data.issue
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db,db:
        db.execute('CREATE TABLE IF NOT EXISTS resource_cache (cache_key TEXT PRIMARY KEY, created REAL NOT NULL, payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS research_requests (requested REAL NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        cached=db.execute('SELECT payload FROM resource_cache WHERE cache_key=? AND created>?',(cache_key,time.time()-86400)).fetchone()
        if cached:return {**json.loads(cached[0]),'action_card':base['action_card'],'cached':True}
        if db.execute('SELECT COUNT(*) FROM research_requests WHERE requested>?',(time.time()-86400,)).fetchone()[0]>=10:
            return {**base,'status':'research_limit_reached'}
        db.execute('INSERT INTO research_requests VALUES (?)',(time.time(),))
    city,state=CITIES[data.city]
    # Only enumerated geography and issue leave our backend. Never include a case
    # number, original_statement, name, phone, PIN, evidence, or payment details.
    request={
        'query':f'Official government labour department complaint procedure and legal assistance for {data.issue.replace("_"," ")} in {city}, {state}, India. Find current official resources, not commercial listings.',
        'type':'auto',
        'numResults':6,
        'includeDomains':DOMAINS,
    }
    # Metadata-only search: no extra summary, answer-generation or content calls.
    # Search results are source discovery, not verified eligibility or jurisdiction.

    try:
        response=httpx.post('https://api.exa.ai/search',headers={'x-api-key':key},json=request,timeout=30)
        response.raise_for_status();sources=extract_sources(response.json())
    except (httpx.HTTPError,ValueError):return {**base,'status':'research_unavailable'}
    result={**base,'status':'sources_found' if sources else 'no_supported_sources','sources':sources,'cached':False}
    with closing(sqlite3.connect(database.DB_PATH,timeout=15)) as db,db:
        db.execute('INSERT OR REPLACE INTO resource_cache VALUES (?,?,?)',(cache_key,time.time(),json.dumps(result)))
    return result

@router.post('/lookup')
def resource_lookup(data:ResourceQuery,request:Request):
    worker.check_json_origin(request)
    worker.rate_limit(['resources:'+(request.client.host if request.client else 'unknown')],limit=20)
    return lookup(data)
