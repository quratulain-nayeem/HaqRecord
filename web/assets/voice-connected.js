const ui=id=>document.getElementById(id);
let call=null,busy=false,ready=false,csrf='',workerCsrf='',draft=null,poll=null,timer=null,lastDraft='';
function updateButtons(){ui('connected-start').disabled=busy||!ready||!ui('connected-consent').checked;ui('connected-stop').disabled=!busy;}
function message(data){return typeof data.detail==='string'?data.detail:data.detail?.message||'Unable to complete this action.';}
async function request(path,method='GET',body=null){
  const response=await fetch(path,{method,headers:{...(body!==null?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRF-Token':csrf}:{})},...(body!==null?{body:JSON.stringify(body)}:{})});
  const data=await response.json();if(!response.ok){const error=new Error(message(data));error.code=data.detail?.code;throw error;}return data;
}
async function refreshDraft(){
  const response=await fetch('/voice/intake/state');if(!response.ok)return;
  const state=await response.json();csrf=state.csrf_token;
  if(state.state==='saved'){
    ui('voice-save-message').textContent=state.result?.payment?.explanation||'Case saved with HaqRecord. No government complaint has been filed.';
    ui('review-content').hidden=true;ui('open-saved-case').hidden=false;
    if(state.case_id)ui('review-heading').textContent='Saved case: '+state.case_id;
    return;
  }
  if(state.state!=='awaiting_browser_approval'||!state.draft)return;
  draft=state;
  if(lastDraft===state.draft_id)return;
  lastDraft=state.draft_id;ui('private-save-consent').checked=false;ui('private-voice-pin').value='';
  ui('voice-distinct-label').hidden=true;ui('voice-distinct').checked=false;ui('voice-save-message').textContent='';
  ui('open-saved-case').hidden=true;ui('review-content').hidden=false;
  const intake=state.draft_kind==='intake';
  ui('private-pin-label').hidden=!intake;ui('private-voice-pin').hidden=!intake;ui('private-voice-pin').required=intake;
  ui('review-heading').textContent=intake?'Review your case before saving':'Confirm the new payment';
  ui('review-description').textContent=intake?'Choose your PIN here, not on the call. This draft is not saved yet.':'This payment is not recorded until you approve it here.';
  if(intake){const c=state.draft.calculation;ui('review-figures').textContent=`Earned ₹${c.total_earned}\nReceived ₹${c.payments_received}\nRemaining ₹${c.balance}\n\n${c.calculation}\n\nBased on the reported account; not a legal determination.`;ui('review-statement').textContent=state.draft.intake.original_statement;}
  else{const p=state.draft.payment;ui('review-figures').textContent=`Additional payment: ₹${p.amount}\nReceived on: ${p.received_on||'Not yet known'}\nMethod: ${p.method}`;ui('review-statement').textContent=p.original_statement;}
}
async function initialize(){
  const status=await(await fetch('/voice/status')).json();ready=status.ready&&status.backend_connected;
  ui('connected-config').textContent=ready?'Bolna and the protected backend tools are configured.':'The backend voice bridge is not ready yet.';
  const response=await fetch('/worker/session');
  if(response.ok){const session=await response.json();workerCsrf=session.csrf_token;ui('worker-access-state').textContent='An existing case is open: '+session.case_id;}
  else ui('worker-access-state').textContent='For updates, first open your case with its reference and PIN using “Open my case”. New intake needs no caseworker login.';
  updateButtons();await refreshDraft();poll=setInterval(()=>refreshDraft().catch(()=>{}),2000);
}
ui('connected-consent').addEventListener('change',updateButtons);
ui('connected-start').addEventListener('click',async()=>{
  if(busy||!ready||!ui('connected-consent').checked)return;
  if(ui('call-mode').value==='existing'&&!workerCsrf){ui('connected-error').textContent='Open your case privately with its reference and PIN first.';return;}
  if(typeof BolnaWebCall==='undefined'){ui('connected-error').textContent='The voice SDK did not load. Refresh the page.';return;}
  busy=true;updateButtons();ui('connected-error').textContent='';ui('connected-status').textContent='Connecting…';
  call=new BolnaWebCall({getSession:async()=>{
    const response=await fetch('/voice/intake/session',{method:'POST',headers:{'Content-Type':'application/json',...(ui('call-mode').value==='existing'?{'X-CSRF-Token':workerCsrf}:{})},body:JSON.stringify({consent_to_voice_processing:true,mode:ui('call-mode').value,language:ui('connected-language').value})});
    const data=await response.json();if(!response.ok)throw new Error(message(data));
    csrf=response.headers.get('X-Voice-CSRF')||'';lastDraft='';draft=null;return data;
  }});
  call.on('state-change',state=>{ui('connected-status').textContent='Call: '+state;});
  call.on('call-start',()=>{});
  call.on('call-end',()=>{clearTimeout(timer);busy=false;updateButtons();ui('connected-status').textContent='Call ended. You can still review and confirm a prepared draft.';if(csrf)request('/voice/intake/end','POST').catch(()=>{});});
  call.on('error',error=>{ui('connected-error').textContent=error.message||'The voice connection failed.';});
  try{await call.start();}catch(error){ui('connected-error').textContent=error.message;try{await call.stop();}catch{}busy=false;updateButtons();}
});
ui('connected-stop').addEventListener('click',async()=>{if(call)await call.stop();});
ui('voice-confirm-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!draft)return;ui('voice-confirm').disabled=true;
  try{
    const body={draft_id:draft.draft_id,approved:true,distinct_payment_confirmed:ui('voice-distinct').checked};
    if(draft.draft_kind==='intake')body.pin=ui('private-voice-pin').value;
    const result=await request('/voice/intake/confirm','POST',body);ui('private-voice-pin').value='';
    if(result.session)workerCsrf=result.session.csrf_token;
    await refreshDraft();
  }catch(error){ui('voice-save-message').textContent=error.message;if(error.code==='possible_duplicate')ui('voice-distinct-label').hidden=false;}
  finally{ui('voice-confirm').disabled=false;}
});
window.addEventListener('pageshow',event=>{if(event.persisted)window.location.reload();});
initialize().catch(()=>{ui('connected-error').textContent='Unable to check the backend. Refresh the page to retry.';});
