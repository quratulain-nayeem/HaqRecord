const el = id => document.getElementById(id);
let workerSession=null, record=null, createOperation=null, paymentOperation=null, checkedCalculation=false;
function panel(name) {
  el('create-panel').hidden=name!=='create';
  el('access-panel').hidden=name!=='access';
  el('case-panel').hidden=name!=='case';
  el('page-error').textContent='';
}
function errorMessage(data) {
  if(typeof data.detail==='string') return data.detail;
  if(data.detail && data.detail.message) return data.detail.message;
  return 'Check the information and try again.';
}
async function api(path, method='GET', body=null) {
  const headers={};
  if(body!==null) headers['Content-Type']='application/json';
  if(workerSession) headers['X-CSRF-Token']=workerSession.csrf_token;
  const response=await fetch(path,{method,headers,...(body!==null?{body:JSON.stringify(body)}:{})});
  const data=await response.json();
  if(!response.ok) {const error=new Error(errorMessage(data));error.status=response.status;error.code=data.detail?.code;throw error;}
  return data;
}
function figures() {
  return {pay_basis:el('basis').value,units_worked:Number(el('units').value),rate_per_unit:el('unit-rate').value,payments_received:el('initial-paid').value};
}
function showCase(data) {
  record=data;panel('case');
  el('case-name').textContent=data.intake.preferred_name;
  el('saved-reference').textContent='Case reference: '+data.case_id;
  el('earned').textContent='₹'+data.calculation.total_earned;
  el('received').textContent='₹'+data.calculation.payments_received;
  el('remaining').textContent='₹'+data.calculation.balance;
  el('saved-arithmetic').textContent=data.calculation.calculation;
  el('original-account').textContent=data.intake.original_statement;
  el('complaint-state').textContent='Complaint: '+(data.complaint_status==='not_prepared'?'not prepared or submitted':data.complaint_status);
  el('questions').replaceChildren();
  for(const question of data.unresolved_questions) {const item=document.createElement('li');item.textContent=question;el('questions').append(item);}
  el('payment-history').replaceChildren();
  const initial=document.createElement('li');initial.textContent=`Initial reported payment: ₹${data.intake.payments_received}. Initial balance: ₹${data.original_calculation.balance}.`;el('payment-history').append(initial);
  for(const event of data.follow_up_payments) {const item=document.createElement('li');item.textContent=`${event.received_on||'Payment date unknown'} · ₹${event.amount} · ${event.method||'Method unknown'} · ${event.explanation}`;el('payment-history').append(item);}
}
el('new-tab').addEventListener('click',()=>panel('create'));
el('existing-tab').addEventListener('click',()=>record?showCase(record):panel('access'));
el('payment-tab').addEventListener('click',()=>{if(record){showCase(record);el('payment-panel').scrollIntoView({behavior:'smooth'});}else panel('access');});
el('create-form').addEventListener('input',()=>{checkedCalculation=false;createOperation=null;el('save-worker-case').disabled=true;el('preview-result').textContent='';});
el('preview').addEventListener('click',async()=>{
  try {const data=await api('/calculate','POST',figures());el('preview-result').textContent=`Earned ₹${data.total_earned} · Received ₹${data.payments_received} · Remaining ₹${data.balance}. ${data.calculation}`;checkedCalculation=true;el('save-worker-case').disabled=false;el('page-error').textContent='';}
  catch(error){el('page-error').textContent=error.message;}
});
el('create-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!checkedCalculation)return;
  el('save-worker-case').disabled=true;createOperation ||= crypto.randomUUID();
  try {
    const result=await api('/worker/cases','POST',{
      ...figures(),preferred_name:el('preferred-name').value,original_statement:el('account').value,
      language:el('worker-language').value,workplace_location:el('workplace').value||null,
      employer_name:el('employer').value||null,pin:el('case-pin').value,operation_id:createOperation,
      consent_to_store:el('store-consent').checked,worker_confirmed:el('facts-confirmed').checked,
    });
    workerSession=result.session;createOperation=null;el('case-pin').value='';showCase(result.case);
  }catch(error){el('page-error').textContent=error.message+' If the connection failed, retry with the same details.';}
  finally{el('save-worker-case').disabled=!checkedCalculation;}
});
el('access-form').addEventListener('submit',async event=>{
  event.preventDefault();el('open-case').disabled=true;
  try {workerSession=await api('/worker/login','POST',{case_id:el('case-reference').value.trim(),pin:el('access-pin').value});el('access-pin').value='';showCase(await api('/worker/my-case'));}
  catch(error){el('page-error').textContent=error.message;}
  finally{el('open-case').disabled=false;}
});
for(const id of ['new-amount','payment-date','payment-method','payment-statement']) el(id).addEventListener('input',()=>{paymentOperation=null;el('duplicate-label').hidden=true;el('distinct-payment').checked=false;});
el('payment-form').addEventListener('submit',async event=>{
  event.preventDefault();el('save-payment').disabled=true;paymentOperation ||= crypto.randomUUID();
  try {
    const result=await api('/worker/payments','POST',{
      operation_id:paymentOperation,amount:el('new-amount').value,received_on:el('payment-date').value||null,
      method:el('payment-method').value,original_statement:el('payment-statement').value,
      worker_confirmed:el('payment-confirmed').checked,distinct_payment_confirmed:el('distinct-payment').checked,
    });
    paymentOperation=null;showCase(result.case);el('payment-form').reset();el('duplicate-label').hidden=true;
    el('payment-message').textContent=result.payment.explanation;
  }catch(error){el('payment-message').textContent=error.message;if(error.code==='possible_duplicate')el('duplicate-label').hidden=false;}
  finally{el('save-payment').disabled=false;}
});
el('close-case').addEventListener('click',async()=>{
  try {await api('/worker/logout','POST');workerSession=null;record=null;window.location.replace('/worker');}
  catch(error){el('page-error').textContent=error.message;}
});
el('download-receipt').addEventListener('click',()=>{
  if(!record)return;
  const text=`HAQRECORD CASE RECEIPT\n${record.case_id}\nSaved with HaqRecord; no government complaint submitted.\n\nWorker-reported account:\n${record.intake.original_statement}\n\n${record.calculation.calculation}\nRemaining reported balance: INR ${record.calculation.balance}\n\nUnresolved:\n${record.unresolved_questions.join('\n')}\n\nPayment history:\n${record.follow_up_payments.map(p=>p.explanation).join('\n')}\n\nBased on supplied figures; not a legal determination.\n`;
  const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download=record.case_id+'-receipt.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
async function initialize(){
  try{const response=await fetch('/worker/session');if(response.ok){workerSession=await response.json();showCase(await api('/worker/my-case'));}}
  catch{el('page-error').textContent='Unable to restore your case session. Use the reference and PIN to open it.';}
}
initialize();

window.addEventListener('pageshow',event=>{if(event.persisted)window.location.reload();});
