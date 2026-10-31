import base64
import io
import json
import os
from pathlib import Path
import sys
import wave
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from PIL import Image
from pypdf import PdfWriter
import reply_sources as sources

png=io.BytesIO();Image.new('RGB',(32,32),'white').save(png,format='PNG');png=png.getvalue()
sources.validate_file('image/png',png)
try:sources.validate_file('image/png',b'\x89PNG\r\n\x1a\nfake');raise AssertionError('Fake image accepted')
except Exception as e:assert not isinstance(e,AssertionError)
with patch('reply_sources.settings',return_value={'SARVAM_API_KEY':'','HAQRECORD_REPLY_MODEL':''}):
    result=sources.extract('image/png',png,'hi');assert result['method']=='not_configured' and result['blocked']
pdf=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=300,height=400);writer.write(pdf)
result=sources.extract('application/pdf',pdf.getvalue(),'en');assert result['unreadable_pages']==[1]
def wav(seconds):
    output=io.BytesIO()
    with wave.open(output,'wb') as audio:audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000);audio.writeframes(b'\0\0'*int(8000*seconds))
    return output.getvalue()
sources.validate_file('audio/wav',wav(1))
try:sources.validate_file('audio/wav',wav(30));raise AssertionError('Oversize duration accepted')
except ValueError:pass
try:sources.validate_file('text/plain',b'\x00binary');raise AssertionError('Binary text accepted')
except ValueError:pass
assert sources.interpret([{'page':1,'text':'Rs ?? was paid on an unreadable date.'}])['assertions']==[]
assert sources.interpret([{'page':1,'text':'Rs 1,00 was paid. Rs 1000e3 unknown. Rs 12.345 unclear.'}])['assertions']==[]
assert sources.interpret([{'page':1,'text':'Rs 1,00,000 was already paid.'}])['assertions'][0]['amount']=='100000'
assert sources.interpret([{'page':1,'text':'I have not paid Rs 1000.'}])['assertions'][0]['kind']=='unknown'
assert sources.interpret([{'page':1,'text':'Please send Rs 1000.'}])['assertions'][0]['kind']=='unknown'
pages=[{'page':1,'text':'Rs 1000 was already paid. Reference DEMO-1.'}]
valid={'assertions':[{'kind':'claimed_payment','excerpt':'Rs 1000 was already paid.','amount':'1000','page':1}],
       'fields':[{'label':'reference','value':'DEMO-1','excerpt':'Reference DEMO-1.','page':1}],
       'explanation_en':'The sender says money was paid. Confirm whether already counted.',
       'explanation_hi':'भेजने वाले ने भुगतान का दावा किया है। पहले से शामिल है या नहीं, पुष्ट करें।',
       'clarification_en':'Was this already counted?','clarification_hi':'क्या यह पहले से हिसाब में है?'}
def response(payload):return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(payload)}}],'usage':{'total_tokens':123}},request=httpx.Request('POST','https://api.sarvam.ai/v2/chat/completions'))
with patch('reply_sources.settings',return_value={'SARVAM_API_KEY':'fictional-test-key','HAQRECORD_REPLY_MODEL':'gemma4'}),patch('reply_sources.httpx.post',return_value=response(valid)) as post:
    result=sources.provider_interpret(pages,'hi');assert result['explanation']==valid['explanation_hi']
    sent=post.call_args.kwargs['json'];assert not sent.get('tools') and 'UNTRUSTED' in sent['messages'][0]['content']
    altered=json.loads(json.dumps(valid));altered['assertions'][0]['amount']='9999';post.return_value=response(altered)
    try:sources.provider_interpret(pages,'en');raise AssertionError('Hallucinated amount accepted')
    except ValueError:pass
    altered=json.loads(json.dumps(valid));altered['fields'][0]['value']='SECRET-OTHER';post.return_value=response(altered)
    try:sources.provider_interpret(pages,'en');raise AssertionError('Invisible reference accepted')
    except ValueError:pass
print('PASS: real type verification; blank PDF requests clarification; WAV duration bound; missing provider is explicit; provider schema/excerpts prevent invented amounts or reference values. Provider HTTP was mocked, no live extraction claim.')
