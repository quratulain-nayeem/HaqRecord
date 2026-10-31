const byId = id => document.getElementById(id);
let session = null, configured = false, call = null, timer = null, busy = false;

function buttons() {
  byId('start-call').disabled = busy || !configured || !session || !byId('voice-consent').checked;
  byId('stop-call').disabled = !busy;
}
async function initialize() {
  const [statusResponse, loginResponse] = await Promise.all([fetch('/voice/status'), fetch('/auth/session')]);
  const status = await statusResponse.json();
  configured = status.ready;

  byId('configuration').textContent = configured ? 'Bolna key and agent ID are configured. A live call has not yet been verified.' : 'Setup needed: add BOLNA_API_KEY and BOLNA_AGENT_ID to the top-level project .env file.';
  if (loginResponse.ok) {
    session = await loginResponse.json();
    byId('login-state').textContent = 'Signed in. Voice testing is limited to the approved account while we validate it.';
  } else {
    byId('login-state').textContent = 'Sign in using Caseworker login, then return here. The fictional calculator demo remains public.';
  }
  buttons();
}
byId('voice-consent').addEventListener('change', buttons);
byId('start-call').addEventListener('click', async () => {
  if (busy || !session || !configured || !byId('voice-consent').checked) return;
  byId('voice-error').textContent = '';byId('execution').textContent='';
  if (!window.isSecureContext) {byId('voice-error').textContent='Microphone access requires localhost or HTTPS.';return;}
  if (typeof BolnaWebCall === 'undefined') {byId('voice-error').textContent='The Bolna SDK did not load. Refresh and try again.';return;}
  busy=true;buttons();byId('call-status').textContent='Connecting…';
  call = new BolnaWebCall({getSession: async () => {
    const response = await fetch('/voice/session', {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},body:JSON.stringify({consent_to_voice_processing:true,language:byId('language').value})});
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail==='string' ? result.detail : 'Unable to start a voice session.');
    return result;
  }});
  call.on('state-change', state => {byId('call-status').textContent='Call: '+state;});
  call.on('call-start', () => {
    const runId=call.getRunId();
    byId('execution').textContent=runId ? 'Bolna execution reference: '+runId : '';
  });
  call.on('call-end', ({reason}) => {clearTimeout(timer);busy=false;buttons();byId('call-status').textContent='Call ended: '+reason;});
  call.on('error', error => {byId('voice-error').textContent=error.message || 'Voice connection failed.';});
  try {await call.start();}
  catch(error) {clearTimeout(timer);byId('voice-error').textContent=error.message || 'Unable to connect.';try {await call.stop();} catch {}busy=false;buttons();}
});
byId('stop-call').addEventListener('click', async () => {if(call) await call.stop();});
initialize().catch(() => {byId('voice-error').textContent='Unable to check the server. Refresh to retry.';});
