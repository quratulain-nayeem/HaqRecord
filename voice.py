"""Bolna browser-call smoke test; provider credentials stay on the server."""
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal

import httpx
from dotenv import dotenv_values
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import auth
from voice_agent_guard import check_agent

router = APIRouter(prefix='/voice', tags=['Browser voice'])


def settings():
    if os.getenv('HAQRECORD_DEMO')=='true':return {'BOLNA_API_KEY':'','BOLNA_AGENT_ID':''}
    # Re-read the local config: load_dotenv may have cached earlier empty values
    # in this running process before the user added their provider credentials.
    file_values = dotenv_values(Path(__file__).resolve().parent / '.env')
    return {
        name: (file_values.get(name) or os.environ.get(name) or '').strip()
        for name in ('BOLNA_API_KEY', 'BOLNA_AGENT_ID')
    }


_callback_health={'url':None,'at':0,'ok':False}

def callback_available(url):
    if not url or not url.startswith('https://'):return False
    if _callback_health['url']==url and time.monotonic()-_callback_health['at']<10:
        return _callback_health['ok']
    try:
        response=httpx.get(url.rstrip('/')+'/health',timeout=4)
        ok=response.status_code==200 and response.json().get('status')=='ok'
    except (httpx.HTTPError,ValueError):ok=False
    _callback_health.update(url=url,at=time.monotonic(),ok=ok)
    return ok


@router.get('/status')
def voice_status():
    values = settings()
    extra={**os.environ,**{k:v for k,v in dotenv_values(Path(__file__).resolve().parent / '.env').items() if v}}
    public=extra.get('HAQRECORD_VOICE_PUBLIC_URL')
    secret=extra.get('HAQRECORD_VOICE_TOOL_SECRET')
    agent_check=check_agent(values,public,tool_secret=secret) if secret else {'ready':False,'status':'not_configured'}
    return {
        'api_key_configured': bool(values.get('BOLNA_API_KEY')),
        'agent_configured': bool(values.get('BOLNA_AGENT_ID')),
        'ready': agent_check['ready'],
        'agent_configuration': agent_check['status'],
        'agent_warnings': agent_check.get('warnings',[]),
        'mode': 'backend_intake',
        'backend_connected': callback_available(public),
        'requires_browser_save_approval': True,
        'cases_are_saved': False,
        'max_duration_seconds': None,
    }


class VoiceStart(BaseModel):
    consent_to_voice_processing: Literal[True]
    language: Literal['hi', 'en'] = 'hi'


@router.post('/session')
def voice_session(data: VoiceStart, session=Depends(auth.require_browser)):
    values = settings()
    key, agent = values.get('BOLNA_API_KEY'), values.get('BOLNA_AGENT_ID')
    if not key or not agent:
        raise HTTPException(503, 'Add BOLNA_API_KEY and BOLNA_AGENT_ID to the project .env first.')
    # Keep request history without a daily quota or retry cooldown.
    with closing(auth.connect()) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS voice_mints (requested_at REAL NOT NULL)')
        db.execute('INSERT INTO voice_mints VALUES (?)', (time.time(),))
    try:
        result = httpx.post(
            'https://api.bolna.ai/web-call/freeswitch-session',
            headers={'Authorization': f'Bearer {key}'},
            json={'agent_id': agent, 'user_data': {
                'language': 'Hindi' if data.language == 'hi' else 'English',
                'haqrecord_mode': 'fictional_voice_smoke_test',
                'section_guidance':'OFF. Use the ordinary HaqRecord conversation.',
                'haqrecord_opening':'नमस्ते, मैं सारा हूँ। आराम से अपनी बात बताएं।' if data.language=='hi' else 'Hello, I am Sara. Tell me what happened, in your own time.',
            }},
            timeout=20,
        )
        if result.status_code in (401, 403):
            raise HTTPException(502, 'Bolna rejected the credentials or browser-call access. Check your account.')
        if result.status_code == 429:
            raise HTTPException(503, 'Bolna is at capacity. Retry later.')
        if not result.is_success:
            raise HTTPException(502, 'Bolna could not create a browser session. Check the agent and credits.')
        payload = result.json()
        if not isinstance(payload, dict):
            raise ValueError('Unexpected response format')
        # Return only the short-lived SDK session, never our long-lived API key.
        return payload
    except httpx.RequestError:
        raise HTTPException(502, 'Unable to reach Bolna. Check the connection and retry.')
    except ValueError:
        raise HTTPException(502, 'Bolna returned an unexpected browser-session response.')
