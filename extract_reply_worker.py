"""Short-lived bounded extraction worker; source data travels through stdin only."""
import base64
import json
import sys
from reply_sources import extract,interpret,provider_interpret


def main():
    data=json.load(sys.stdin)
    extraction=extract(data['mime'],base64.b64decode(data['content_base64'],validate=True),data['language'])
    try:analysis=provider_interpret(extraction['pages'],data['language']) if extraction['pages'] else interpret([],data['language'])
    except Exception:
        analysis=interpret(extraction['pages'],data['language'])
        analysis['provider_interpretation_failed']=True
        analysis['notice']='Provider interpretation failed. Only literal amounts are shown; review the original and clarify the meaning yourself.'
    result={**extraction,**analysis}
    status='blocked' if extraction.get('blocked') else 'needs_clarification' if extraction.get('unreadable_pages') or not any(p['text'].strip() for p in extraction['pages']) else 'ready_for_review'
    sys.stdout.buffer.write(json.dumps({'result':result,'status':status},ensure_ascii=False).encode('utf-8'))


if __name__=='__main__':
    try:main()
    except Exception:
        # No source content, provider responses or credentials in stderr.
        raise SystemExit(1)
