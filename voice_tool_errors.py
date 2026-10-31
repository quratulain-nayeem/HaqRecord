"""Safe tool errors: no request values, secrets or internal stack traces."""
import logging
from contextlib import closing
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger=logging.getLogger('haqrecord.voice.validation')


async def validation_error(request, error:RequestValidationError):
    fields=sorted({str(e['loc'][1]) for e in error.errors() if len(e['loc'])>1})
    logger.warning('Voice tool rejected: path=%s fields=%s codes=%s',request.url.path,fields,
                   sorted({e['type'] for e in error.errors()}))
    internal='voice_token' in fields
    # A rejected correction must not leave an obsolete unsaved balance available
    # for approval. Authenticate before touching this call's private context.
    from voice_backend import require_tool,context_by,connect
    import auth
    try:
        require_tool(request)
        body=error.body if isinstance(error.body,dict) else {}
        token=body.get('voice_token')
        context=context_by('tool_hash',auth.digest(token)) if isinstance(token,str) and 20<=len(token)<=256 else None
        if context and not context['case_id'] and request.url.path in ('/bolna/tools/calculate','/bolna/tools/prepare-case'):
            with closing(connect()) as db,db:
                db.execute("UPDATE voice_contexts SET preview_json=NULL,next_step_json=NULL,draft_id=NULL,draft_kind=NULL,draft_json=NULL,draft_hash=NULL,state='needs_clarification' WHERE context_id=? AND case_id IS NULL AND state!='committing'",(context['context_id'],))
    except HTTPException:
        pass
    return JSONResponse(status_code=422,content={
        'status':'not_updated','on_screen':False,'saved':False,
        'invalid_fields':fields,
        'spoken_response':('I couldn’t update the figures. Please reconnect and we can continue.' if internal else
                           'I haven’t updated the figures yet. Let me check the details you already gave me.'),
        'instructions':('Use the internal voice_token from the call context. Never ask the worker for tokens or credentials. If unavailable, ask them to reconnect.' if internal else
                        'Retry once using the confirmed facts and these field names. Do not ask the worker to repeat known answers, optional employer details, payment dates or payment methods to repair a tool request. Ask one natural question only if an essential wage fact is genuinely missing. Never mention backend, API, validation or tools. Never say the screen updated or a case saved until a successful response confirms it.')})
