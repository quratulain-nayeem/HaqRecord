"""Real headless Chromium UI test, isolated from all existing worker records."""
import base64
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.tools/resolution-review'
OUT.mkdir(parents=True,exist_ok=True)
chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
if not chrome.exists():raise SystemExit('Install Chrome or configure the browser executable in this test. No browser test was run.')
with tempfile.TemporaryDirectory(prefix='haqrecord-browser-') as folder:
    temp=Path(folder)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ,'HAQRECORD_DB_PATH':str(temp/'cases.db'),'HAQRECORD_AUTH_DB_PATH':str(temp/'auth.db'),'HAQRECORD_DEMO':'true','SESSION_COOKIE_SECURE':'false'}
    with (temp/'server.log').open('wb') as log:
        server=subprocess.Popen([sys.executable,'-B','-m','uvicorn','main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(80):
            try:
                if httpx.get(base+'/health',timeout=1).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.15)
        else:raise AssertionError('Isolated test server failed to start')
        api=httpx.Client(base_url=base,timeout=20)
        saved=api.post('/worker/cases',json={'operation_id':str(uuid4()),'pin':'928371','preferred_name':'Fictional worker',
            'original_statement':'Fictional five days at 1000 each; 1000 wages received.','language':'en','pay_basis':'daily','units_worked':5,'rate_per_unit':'1000','payments_received':'1000',
            'workplace_location':'Hyderabad','consent_to_store':True,'worker_confirmed':True,'adjustments_checked':True}).json()
        headers={'X-CSRF-Token':saved['session']['csrf_token']}
        message="Rs 1,000 was already given as advance. I'll send Rs 1,500 on Friday and the rest later."
        source=api.post('/worker/resolution/sources',headers=headers,json={'operation_id':str(uuid4()),'filename':'employer-message.txt','mime':'text/plain','content_base64':base64.b64encode(message.encode()).decode(),'origin':'employer_message','message_date':'2026-10-29','fictional':True,'language':'en','consent_to_store':True})
        assert source.status_code==202,source.text
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=str(chrome),headless=True)
            page=browser.new_page(viewport={'width':360,'height':800},device_scale_factor=1)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base);page.locator('#lang-en').click();page.locator('#action-case').click()
            page.locator('#case-reference').fill(saved['case']['case_id']);page.locator('#access-pin').fill('928371');page.locator('#open-case').click()
            page.locator('#resolution-tab-reply').wait_for()
            assert page.locator('#resolution-body').is_hidden(), 'Long forms should not open until chosen'
            assert page.locator('#case-workspace .workspace-advanced').get_attribute('open') is None
            page.screenshot(path=str(OUT/'simple-case-mobile-en.png'))
            page.locator('#resolution-tab-reply').click()
            page.locator('#res-source-view').wait_for()
            assert '4,000' in page.locator('#case-remaining').inner_text()
            assert message in page.locator('#res-source-view').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'),'Mobile content overflow'
            page.screenshot(path=str(OUT/'case-mobile-en.png'))
            page.locator('#res-advance').select_option('yes');page.locator('#res-clarification').fill('The 1000 advance was already counted.');page.locator('#res-review-confirm').check();page.locator('#res-review button[type=submit]').click()
            page.wait_for_function("()=>document.querySelector('#resolution-status')?.textContent.includes('Saved')")
            page.locator('#res-go-promise').click();page.locator('#res-promise-amount').fill('1500');page.locator('#res-promise-date').fill('2026-11-06');page.locator('#res-promise-date-text').fill('Friday');page.locator('#res-promise-statement').fill('1500 promised; remaining date unspecified.');page.locator('#res-promise-confirm').check();page.locator('#res-promise-form button[type=submit]').click()
            page.wait_for_function("()=>document.querySelector('#resolution-status')?.textContent.includes('Saved')")
            assert '4,000' in page.locator('#case-remaining').inner_text()
            def tab(name):
                summary=page.locator('#resolution > details.more-actions > summary').first
                if not page.locator('#resolution-tab-'+name).is_visible():summary.click()
                page.locator('#resolution-tab-'+name).click()
            tab('request');page.locator('#res-work-period').fill('Five confirmed days');page.locator('#res-request-confirm').check();page.locator('#res-request-form button[type=submit]').click();page.locator('#res-request-text').wait_for();page.locator('#res-request-approve').click()
            page.wait_for_function("()=>document.querySelector('#resolution-status')?.textContent.includes('approved')")
            assert not page.locator('#res-request-copy').is_disabled()
            page.locator('#lang-hi').click();page.wait_for_function("()=>document.querySelector('#resolution')?.textContent.includes('आप क्या करना चाहते हैं?')")
            assert '4,000' in page.locator('#case-remaining').inner_text()
            page.locator('#resolution').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'case-mobile-hi.png'))
            # Language changes retain in-progress form fields and approved snapshot.
            page.locator('#res-work-period').fill('A preserved draft field');page.locator('#lang-en').click()
            page.wait_for_function("()=>document.querySelector('#res-work-period')?.value==='A preserved draft field'")
            tab('reminder')
            assert page.locator('#res-reminder-date').is_visible()
            assert not page.locator('#res-payment-amount').is_visible()
            assert not page.locator('#res-promise-amount').is_visible()
            page.screenshot(path=str(OUT/'simple-reminder-mobile-en.png'))
            tab('payment');page.locator('#res-payment-promise').select_option(index=1);page.locator('#res-payment-amount').fill('1500');page.locator('#res-payment-statement').fill('1500 actually arrived for this case.');page.locator('#res-payment-confirm').check();page.locator('#res-payment-form button[type=submit]').click()
            page.wait_for_function("()=>document.querySelector('#case-remaining')?.textContent.includes('2,500')")
            tab('diary');page.locator('#res-diary-place').fill('Fictional site');page.locator('#res-diary-rate').fill('700');page.locator('#res-diary-statement').fill('Today one day at 700; no money received.');page.locator('#res-diary-confirm').check();page.locator('#res-diary-form button[type=submit]').click()
            page.wait_for_function("()=>document.querySelector('#res-diary-entries')?.textContent.includes('700')")
            assert '2,500' in page.locator('#case-remaining').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            # A focused advanced field must translate without discarding an edit.
            advanced=page.locator('#case-workspace > details > summary');advanced.click()
            page.locator('#case-workspace > details > details > summary').first.click()
            page.locator('#workspace-rate').fill('875')
            page.locator('#workspace-rate').focus()
            page.evaluate("setLanguage('hi')")
            assert page.locator('#workspace-rate').input_value()=='875'
            assert 'तय रुपये' in page.locator('#workspace-rate').locator('..').inner_text()
            page.evaluate("setLanguage('en')")
            assert page.locator('#workspace-rate').input_value()=='875'
            assert 'Agreed rupees' in page.locator('#workspace-rate').locator('..').inner_text()
            # Real UI + a deterministic SDK double: scope, draft fill and controls.
            assert page.locator('#case-workspace [data-section-start]').count()==5
            section_requests=[];section_state={};file_requests=[]
            def scoped_session(route):
                payload=route.request.post_data_json;section_requests.append(payload)
                section_state.clear();section_state.update({'section':payload['section'],'values':payload['section_values'],
                    'revision':0,'status':'asking','read_only':False,'next_question':'One field in this block only.'})
                route.fulfill(status=200,headers={'X-Voice-CSRF':'fictional-section-csrf'},json={'run_id':'fictional-ui-call'})
            page.route('**/voice/intake/session',scoped_session)
            page.route('**/voice/intake/section-state',lambda route:route.fulfill(json=section_state))
            page.route('**/voice/intake/end',lambda route:route.fulfill(json={'status':'voice_tools_revoked'}))
            def selected_file(route):
                file_requests.append(route.request.post_data_json);route.fulfill(json={'saved':False})
            page.route('**/voice/intake/section-file',selected_file)
            page.evaluate("""() => {
                window.__sectionStops=0;
                navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop(){}}]});
                window.BolnaWebCall=class {
                    constructor(options){this.options=options;this.events={};}
                    on(name,fn){this.events[name]=fn;}
                    async start(){await this.options.getSession();this.events['call-start']?.();}
                    async stop(){window.__sectionStops++;this.events['call-end']?.({reason:'local-hangup'});}
                };
            }""")
            agreement=page.locator('[data-workspace-section=agreement]')
            agreement.locator('[data-section-start]').click();agreement.locator('[data-section-consent]').check()
            agreement.locator('[data-section-start]').click()
            agreement.locator('[data-section-pause]').wait_for()
            section_state['values']={**section_state['values'],'workspace-rate':'1250'};section_state['revision']=1
            page.wait_for_function("()=>document.querySelector('#workspace-rate').value==='1250'")
            assert not page.locator('#workspace-approve').is_checked()
            agreement.locator('[data-section-pause]').click()
            page.wait_for_function('()=>!busy')
            assert page.evaluate('__sectionStops')>=1
            agreement.locator('[data-section-start]').click()
            page.wait_for_function('()=>busy');agreement.locator('[data-section-pause]').click();page.wait_for_function('()=>!busy')
            assert section_requests[-1]['section']=='agreement' and not section_requests[-1]['restart_section']
            agreement.locator('[data-section-restart]').click()
            page.wait_for_function("()=>document.querySelector('#workspace-rate').value==='875'")
            assert section_requests[-1]['restart_section']
            agreement.locator('[data-section-end]').click();page.wait_for_function('()=>!busy')
            page.locator('#lang-hi').click()
            evidence=page.locator('[data-workspace-section=evidence]');evidence.locator('summary').click()
            evidence.locator('[data-section-start]').click();evidence.locator('[data-section-consent]').check();evidence.locator('[data-section-start]').click()
            evidence.locator('[data-section-pause]').wait_for()
            page.locator('#workspace-file').set_input_files({'name':'fictional-section.txt','mimeType':'text/plain','buffer':b'Fictional material only'})
            page.wait_for_function("()=>document.querySelector('[data-workspace-section=evidence] [data-section-status]').textContent.includes('फ़ाइल चुनी गई')")
            assert file_requests[-1]['filename']=='fictional-section.txt'
            assert section_requests[-1]['language']=='hi' and section_requests[-1]['section']=='evidence'
            page.screenshot(path=str(OUT/'section-voice-mobile-hi.png'))
            evidence.locator('[data-section-end]').click();page.wait_for_function('()=>!busy')
            page.locator('#lang-en').click()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            print('PASS: five block microphones; scoped SDK payloads; voice answers fill only local fields; pause/continue/restart; final approval stays unchecked; Hindi file selection stays browser-only.')
            # Keyboard activation checks the control, not actual audible provider performance.
            page.evaluate("window.__spoken=0;speechSynthesis.speak=()=>{window.__spoken++}")
            page.locator('#resolution-summary').focus();page.keyboard.press('Space')
            assert page.evaluate('window.__spoken>0')
            assert page.locator('#reading-controls').is_visible()
            page.evaluate("window.__audio=[];speechSynthesis.pause=()=>__audio.push('pause');speechSynthesis.resume=()=>__audio.push('resume');speechSynthesis.cancel=()=>__audio.push('cancel')")
            page.locator('#reading-pause').click();assert 'Continue listening' in page.locator('#reading-pause').inner_text()
            page.locator('#reading-pause').click();assert page.evaluate('__audio.includes(\'resume\')')
            page.locator('#reading-restart').click();assert page.evaluate('__spoken>1')
            page.locator('#lang-hi').click();assert page.locator('#reading-controls').is_hidden()
            page.locator('#listen-guide').click();page.locator('#reading-pause').click()
            assert 'आगे सुनें' in page.locator('#reading-pause').inner_text()
            page.screenshot(path=str(OUT/'help-controls-mobile-hi.png'))
            page.locator('#reading-restart').click();page.locator('#reading-stop').click()
            assert page.locator('#reading-controls').is_hidden()
            page.locator('#lang-en').click()
            assert not errors,errors
            report=page.request.get(base+'/worker/resolution/packet');assert report.status==200
            printable=browser.new_page(viewport={'width':794,'height':1123});printable.set_content(report.text());printable.screenshot(path=str(OUT/'printable-report.png'))
            assert 'तैयारी' in printable.locator('body').inner_text()
            assert printable.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            printable.close()
            page.set_viewport_size({'width':1280,'height':900});tab('reply');page.locator('#resolution').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'case-desktop.png'))
            print('PASS: real browser 360px and desktop; reply review, promise, exact request approval, language continuity, actual payment, separate diary, keyboard read-aloud activation; no JS errors or mobile overflow.')
            # Figure review from the reported screenshot: real layout in both languages.
            review=browser.new_page(viewport={'width':360,'height':800})
            review_errors=[];review.on('pageerror',lambda error:review_errors.append(str(error)))
            preview={'preview_id':'fictional-ui-review','original_statement':'Fictional account only.',
                'preferred_name':'Fictional worker','workplace_location':'Hyderabad','employer_name':'',
                'calculation':{'total_earned':'4000.00','payments_received':'1000.00','balance':'3000.00',
                    'units_worked':4,'pay_basis':'weekly','rate_per_unit':'1000.00'}}
            import json
            review.route('**/voice/intake/state*',lambda route:route.fulfill(json={'state':'listening','csrf_token':'fictional-csrf','preview':preview}))
            review.goto(base);review.locator('#hero-speak').click();review.locator('#draft-review').wait_for()
            review.locator('#preview-story').fill('Keep this private draft text')
            review.locator('#voice-pin').fill('684295')
            for lang in ('hi','en'):
                review.locator('#lang-'+lang).click()
                review.locator('#read-draft').scroll_into_view_if_needed()
                hear=review.locator('#read-draft').bounding_box();correct=review.locator('#correct-by-voice').bounding_box()
                assert hear['y']+hear['height']<=correct['y'], 'Review buttons overlap'
                assert hear['height']>=48 and correct['height']>=48
                assert review.locator('#preview-story').input_value()=='Keep this private draft text'
                assert review.locator('#voice-pin').input_value()=='684295'
                assert review.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                review.screenshot(path=str(OUT/f'figure-controls-mobile-{lang}.png'))
            review.set_viewport_size({'width':320,'height':740})
            assert review.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            review.set_viewport_size({'width':1280,'height':900})
            review.locator('#read-draft').scroll_into_view_if_needed()
            hear=review.locator('#read-draft').bounding_box();correct=review.locator('#correct-by-voice').bounding_box()
            assert hear['x']+hear['width']<=correct['x'] or hear['y']+hear['height']<=correct['y']
            review.screenshot(path=str(OUT/'figure-controls-desktop-en.png'))
            assert not review_errors,review_errors
            review.close()
            print('PASS: 360px Hindi/English figure-review buttons do not overlap; draft edits and PIN survive switching; no overflow or JS errors.')
            # A fresh browser can create a diary without having a wage dispute.
            page=browser.new_page(viewport={'width':360,'height':800});page.goto(base);page.locator('#lang-en').click();page.locator('#action-payment').click();page.locator('#res-book-pin').fill('928371');page.locator('#res-book-consent').check();page.locator('#res-diary-create button[type=submit]').click();page.locator('#res-diary-form').wait_for()
            assert page.locator('.case-balances').is_hidden()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            print('PASS: home work-diary entry creates a separate private diary with no wage dispute; 360px dialog and return flow work.')
            browser.close()
    finally:
        server.terminate();server.wait(timeout=10)
