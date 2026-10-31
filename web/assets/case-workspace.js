/* Case workspace uses the existing private worker session; no PIN reaches voice tools. */
(() => {
  const copy = {
    en: {title:'Build your case record',next:'Next useful question',reconstruct:'Check the agreement and payments',
      agreement:'Agreement',basis:'Payment basis',daily:'Daily',weekly:'Weekly',monthly:'Monthly',units:'Confirmed quantity in this unit',rate:'Agreed rupees per unit',
      payments:'Payments in the original account (later recorded payments stay separate)',add:'Add a payment or promise',
      amount:'Amount (₹)',status:'What happened?',received:'Received',promised:'Promised only',allocation:'Which job?',
      thisCase:'This case',other:'Another job',unknown:'Not yet clear',confirmed:'I confirmed this payment belongs to this case',
      statement:'What was said about this payment?',source:'Source',account:'Worker’s account',remove:'Remove from this revision',
      rateSource:'Source for agreed rate',unitsSource:'Source for completed work',reason:'What changed or remains uncertain?',
      preview:'Check these figures',save:'Confirm and save correction',approve:'I checked these facts and the unresolved points.',
      evidence:'Add supporting material and link facts',file:'PNG, JPEG, PDF or text (up to 5 MB)',description:'What does this material relate to?',
      fictional:'Fictional material for the demo',store:'I agree to store this supporting material with this case',upload:'Upload supporting material',
      evidenceNote:'An upload is supporting material, not independent verification. Read it, link what it shows, and confirm which job a payment concerns.',
      fact:'Fact',value:'What does the source say?',unresolved:'What still needs confirmation?',link:'Link this fact to its source',
      factConfirm:'I confirm this interpretation; the material is not independently verified',
      followup:'Follow up on this case',when:'When should this appear?',action:'What will you do?',consent:'Show this reminder when I open my case',
      remind:'Save in-app reminder',reminderNote:'Reminders appear when you open this case. No SMS, telephone calls or background notifications are sent.',
      due:'Due now',pending:'Pending',completed:'Completed',none:'No reminder selected',reminder:'Reminder being followed up',
      outcome:'Follow-up outcome',newPayment:'Money received for this case',noPayment:'No money received',date:'Date received (if known)',method:'Method',
      cash:'Cash',transfer:'Transfer',methodUnknown:'Unknown',followStatement:'What happened?',followConfirm:'I confirm the outcome and that it concerns this case',
      distinct:'This is a separate new payment, even if another entry looks the same',record:'Confirm follow-up',
      packet:'Download case packet',packetNote:'ZIP includes a printable HTML report, case JSON and original supporting files. No government complaint is submitted.',
      facts:'Facts and their sources',timeline:'Case history',empty:'No supporting files supplied yet.',version:'Revision',
      earned:'Earned',allocated:'Wages received for this work',unallocated:'Received money needing clarification',promiseTotal:'Promised, not received',
      balance:'Remaining before unclear payments',conditional:'If all unclear payments belong to this work',provisional:'Provisional: clarify the unresolved points before treating the balance as final.',
      saved:'Saved. The original account and earlier revisions are preserved.',noteOnly:'Source notes do not change the balance. Review payment allocation above to change the calculation.',
      reload:'Your case changed. Reload the case and review its current version.',needPreview:'Check the figures before confirming this correction.'},
    hi: {title:'अपने मामले का रिकॉर्ड तैयार करें',next:'अगला ज़रूरी सवाल',reconstruct:'समझौता और मिले पैसे जांचें',
      agreement:'समझौता',basis:'मज़दूरी का आधार',daily:'दैनिक',weekly:'साप्ताहिक',monthly:'मासिक',units:'कुल काम के दिन / हफ़्ते / महीने',rate:'हर दिन / हफ़्ते / महीने तय रुपये',
      payments:'शुरुआती खाते के भुगतान (बाद के भुगतान अलग रखे जाते हैं)',add:'भुगतान या वादा जोड़ें',amount:'रकम (₹)',status:'क्या हुआ?',
      received:'पैसे मिले',promised:'सिर्फ़ वादा हुआ',allocation:'किस काम के पैसे?',thisCase:'इस मामले के',other:'दूसरे काम के',unknown:'अभी स्पष्ट नहीं',
      confirmed:'मैंने पुष्टि की है कि यह भुगतान इस मामले का है',statement:'इस भुगतान के बारे में क्या बताया?',source:'स्रोत',account:'मज़दूर की बताई बात',remove:'इस नए संशोधन से हटाएं',
      rateSource:'तय मज़दूरी का स्रोत',unitsSource:'किए गए काम का स्रोत',reason:'क्या बदला या क्या स्पष्ट नहीं है?',preview:'हिसाब जांचें',save:'पुष्टि करके सुधार सुरक्षित करें',
      approve:'मैंने जानकारी और अनसुलझे सवाल जांच लिए हैं।',evidence:'सहायक दस्तावेज़ जोड़ें और जानकारी से लिंक करें',file:'PNG, JPEG, PDF या टेक्स्ट (अधिकतम 5 MB)',
      description:'यह सामग्री किस बारे में है?',fictional:'डेमो के लिए काल्पनिक सामग्री',store:'मैं यह सामग्री अपने मामले के साथ रखना चाहता/चाहती हूँ',upload:'सहायक सामग्री अपलोड करें',
      evidenceNote:'अपलोड अपने आप सत्यापन नहीं है। सामग्री देखकर बताएं कि उसमें क्या है और भुगतान किस काम का है।',fact:'जानकारी',value:'स्रोत में क्या बताया गया है?',unresolved:'अभी क्या पुष्टि करनी है?',
      link:'जानकारी को स्रोत से जोड़ें',factConfirm:'मैं इस अर्थ की पुष्टि करता/करती हूँ; सामग्री की स्वतंत्र जांच नहीं हुई है',followup:'इसी मामले की आगे की बात',
      when:'यह याद कब दिखाएं?',action:'आप क्या करेंगे?',consent:'मामला खोलने पर यह याद दिखाएं',remind:'वेबसाइट में याद सुरक्षित करें',
      reminderNote:'याद मामला खोलने पर दिखेगी। SMS, फ़ोन कॉल या बैकग्राउंड सूचना नहीं भेजी जाएगी।',due:'अब समय हो गया है',pending:'बाकी',completed:'पूरा हुआ',none:'कोई याद नहीं चुनी',reminder:'किस याद पर आगे की बात है?',
      outcome:'आगे क्या हुआ?',newPayment:'इस मामले के पैसे मिले',noPayment:'कोई पैसा नहीं मिला',date:'पैसे मिलने की तारीख (पता हो तो)',method:'कैसे मिले?',cash:'नकद',transfer:'ट्रांसफ़र',methodUnknown:'पता नहीं',
      followStatement:'क्या हुआ?',followConfirm:'मैं परिणाम और इसी मामले से संबंध की पुष्टि करता/करती हूँ',distinct:'मिलती-जुलती एंट्री होने पर भी यह अलग नया भुगतान है',record:'आगे की बात सुरक्षित करें',
      packet:'मामले का पैकेट डाउनलोड करें',packetNote:'ZIP में प्रिंट योग्य HTML रिपोर्ट, मामले की जानकारी और मूल सहायक फ़ाइलें होंगी। सरकारी शिकायत नहीं भेजी जाती।',
      facts:'जानकारी और उसके स्रोत',timeline:'मामले का इतिहास',empty:'अभी कोई सहायक फ़ाइल नहीं दी गई है।',version:'संशोधन',earned:'कुल कमाई',allocated:'इस काम के मिले पैसे',
      unallocated:'पैसे मिले, काम स्पष्ट नहीं',promiseTotal:'वादा, पैसे नहीं मिले',balance:'अनिश्चित भुगतान जोड़ने से पहले बाकी',conditional:'अगर सभी अनिश्चित पैसे इसी काम के हों',
      provisional:'अस्थायी हिसाब: अंतिम रकम मानने से पहले अनसुलझी बातें स्पष्ट करें।',saved:'सुरक्षित हुआ। मूल बात और पुराने संशोधन रखे गए हैं।',
      noteOnly:'स्रोत की टिप्पणी रकम नहीं बदलती। हिसाब बदलने के लिए ऊपर भुगतान का काम और पुष्टि जांचें।',reload:'मामला बदल गया है। नया रिकॉर्ड खोलकर फिर जांचें।',needPreview:'सुधार सुरक्षित करने से पहले हिसाब जांचें।'},
  };
  let record=null,lang='hi',checkedSnapshot='',checkedVersion=0;
  const operations=new Map();
  const $=id=>document.getElementById(id), t=key=>copy[lang][key]||copy.en[key]||key;
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const option=(value,label)=>`<option value="${esc(value)}">${esc(label)}</option>`;
  const label=(key,field)=>`<label>${esc(t(key))}${field}</label>`;
  const input=(id,attrs='')=>`<input id="${id}" ${attrs}>`;
  const button=(id,key)=>`<button class="outline" id="${id}" type="submit">${esc(t(key))}</button>`;
  const checkbox=(id,key)=>`<label class="consent-line">${input(id,'type="checkbox" required')}<span>${esc(t(key))}</span></label>`;
  function op(key,body){const hash=JSON.stringify(body),old=operations.get(key);if(old?.hash===hash)return old.id;const id=crypto.randomUUID();operations.set(key,{hash,id});return id;}
  async function api(path,body){
    const session=await fetch('/worker/session');if(!session.ok)throw new Error('Open this case again using its reference and PIN.');
    const auth=await session.json();
    const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':auth.csrf_token},body:JSON.stringify(body)});
    const data=await response.json();if(!response.ok){const e=new Error(typeof data.detail==='string'?data.detail:data.detail?.message||'Check the information and try again.');e.code=data.detail?.code;throw e;}return data;
  }
  function message(text){$('workspace-message').textContent=text;$('workspace-message').hidden=!text;}
  function summary(c){
    return `<dl class="workspace-summary">${[['earned',c.total_earned],['allocated',c.payments_received],['unallocated',c.unallocated_received||'0.00'],['promiseTotal',c.promised_amount||'0.00'],['balance',c.balance]].map(([k,v])=>`<div><dt>${esc(t(k))}</dt><dd>₹${esc(v)}</dd></div>`).join('')}</dl>`+
      (c.provisional?`<p>${esc(t('provisional'))}</p><p>${esc(t('conditional'))}: ₹${esc(c.balance_if_unallocated_applies)}</p>`:'')+
      (c.next_question?`<p>${esc(lang==='hi'?(c.next_question_hi||c.next_question):c.next_question)}</p>`:'');
  }
  function sourceLabel(id){return id==='worker_account'?t('account'):record?.workspace.sources.find(s=>s.source_id===id)?.filename||id;}
  function sourceOptions(){return option('worker_account',t('account'))+(record?.workspace.sources||[]).map(s=>option(s.source_id,`${s.filename}${s.fictional?' [DEMO]':''}`)).join('');}
  function factLabel(key){return ({rate_per_unit:t('rate'),units_worked:t('units'),payment_amount:t('amount'),workplace_location:lang==='hi'?'काम की जगह':'Workplace',employer_name:lang==='hi'?'मालिक':'Employer',other:lang==='hi'?'अन्य':'Other'})[key]||key;}
  function paymentRow(payment={}){
    const row=document.createElement('fieldset');row.className='workspace-payment';row.dataset.paymentId=payment.payment_id||crypto.randomUUID();
    row.innerHTML=label('amount','<input data-payment="amount" type="number" min="0.01" step="0.01" required>')+
      label('status',`<select data-payment="status">${option('received',t('received'))+option('promised',t('promised'))}</select>`)+
      label('allocation',`<select data-payment="allocation">${option('unresolved',t('unknown'))+option('this_case',t('thisCase'))+option('other_job',t('other'))}</select>`)+
      label('method',`<select data-payment="method">${option('unknown',t('methodUnknown'))+option('cash',t('cash'))+option('transfer',t('transfer'))}</select>`)+
      label('date','<input data-payment="received_on" type="date">')+
      label('statement','<textarea data-payment="statement" maxlength="2000" required></textarea>')+
      label('source',`<select data-payment="source_id">${sourceOptions()}</select>`)+
      `<label class="consent-line"><input data-payment="worker_confirmed" type="checkbox"><span>${esc(t('confirmed'))}</span></label>`+
      `<button type="button" class="text-button">${esc(t('remove'))}</button>`;
    for(const key of ['amount','status','allocation','method','received_on','statement']){const node=row.querySelector(`[data-payment="${key}"]`);if(payment[key]!=null)node.value=payment[key];}
    row.querySelector('[data-payment="source_id"]').value=payment.source_ids?.[0]||'worker_account';
    row.querySelector('[data-payment="worker_confirmed"]').checked=!!payment.worker_confirmed;
    // Preserve multiple source references supplied by voice when the selection is unchanged.
    row.dataset.sources=JSON.stringify(payment.source_ids||['worker_account']);
    row.querySelector('button').addEventListener('click',()=>{row.remove();invalidate();});
    $('workspace-payments').append(row);
  }
  function snapshot(){
    const payments=Array.from($('workspace-payments').children).map(row=>{
      const value=key=>row.querySelector(`[data-payment="${key}"]`).value;
      const old=JSON.parse(row.dataset.sources),source=value('source_id');
      return {payment_id:row.dataset.paymentId,amount:value('amount'),status:value('status'),allocation:value('allocation'),method:value('method'),
        received_on:value('received_on')||null,statement:value('statement'),worker_confirmed:row.querySelector('[data-payment="worker_confirmed"]').checked,
        source_ids:old[0]===source?old:[source]};
    });
    return {work_periods:record.workspace.reconstruction?.work_periods||[],pay_basis:$('workspace-basis').value,units_worked:Number($('workspace-units').value),rate_per_unit:$('workspace-rate').value,payments,
      unresolved_questions:$('workspace-open-questions').value.split('\n').map(q=>q.trim()).filter(Boolean),
      fact_sources:{...(record.workspace.reconstruction?.fact_sources||{}),...Object.fromEntries(['rate_per_unit','units_worked'].map((key,i)=>{
        const old=record.workspace.reconstruction?.fact_sources?.[key]||[],value=$(i?'workspace-units-source':'workspace-rate-source').value;
        return [key,old[0]===value?old:[value]];
      }))}};
  }
  function invalidate(){checkedSnapshot='';$('workspace-save').disabled=true;$('workspace-approve').checked=false;$('workspace-preview').replaceChildren();}
  async function action(form,fn){
    const buttons=Array.from(form.querySelectorAll('button'));buttons.forEach(b=>b.disabled=true);
    try{message('');await fn();}catch(e){message(e.message);}
    finally{buttons.forEach(b=>b.disabled=false);if($('workspace-save'))$('workspace-save').disabled=!checkedSnapshot;}
  }
  function refreshCase(data){renderCase(data);message(t('saved'));}
  function render(data){if(data.record_type==='work_diary'&&!data.workspace.reconstruction){$('case-workspace')?.remove();return;}
    const existing=$('case-workspace');const nextLang=document.documentElement.lang==='en'?'en':'hi';
    const changingLanguage=!!existing&&lang!==nextLang;
    if(existing?.contains(document.activeElement)&&!changingLanguage)return;
    const edits=changingLanguage?Array.from(existing.querySelectorAll('input[id],textarea[id],select[id]')).map(n=>({id:n.id,value:n.value,checked:n.checked,files:n.files,type:n.type})):[];
    const opened=changingLanguage?Array.from(existing.querySelectorAll('details')).map(n=>n.open):[];
    const rows=changingLanguage?snapshot().payments:null;
    record=data;lang=document.documentElement.lang==='en'?'en':'hi';checkedSnapshot='';
    const section=existing||document.createElement('section');section.id='case-workspace';section.className='case-workspace';section.dataset.caseId=data.case_id;
    section.innerHTML=`<details class="workspace-advanced"><summary>${esc(lang==='hi'?'जानकारी सुधारें या पूरे कागज़ देखें':'Correct details or see all records')}</summary><h2>${esc(t('title'))}</h2><p><strong>${esc(t('next'))}:</strong> ${esc(lang==='hi'?data.workspace.next_question_hi:data.workspace.next_question)}</p>`+
      `<div>${summary(data.calculation)}</div>`+
      `<details data-workspace-section="agreement"><summary>${esc(t('reconstruct'))}</summary><form id="workspace-reconstruction-form">`+
      label('basis',`<select id="workspace-basis">${option('daily',t('daily'))+option('weekly',t('weekly'))+option('monthly',t('monthly'))+option('hourly',lang==='hi'?'घंटे की दर':'Hourly')+option('piece',lang==='hi'?'इकाई की दर':'Per piece')}</select>`)+
      label('units',input('workspace-units','type="number" min="0.001" max="10000" step="0.001" required'))+
      label('rate',input('workspace-rate','type="number" min="0.01" step="0.01" required'))+
      label('rateSource',`<select id="workspace-rate-source">${sourceOptions()}</select>`)+
      label('unitsSource',`<select id="workspace-units-source">${sourceOptions()}</select>`)+
      `<h3>${esc(t('payments'))}</h3><div id="workspace-payments"></div><button id="workspace-add" class="text-button" type="button">${esc(t('add'))}</button>`+
      label('reason','<textarea id="workspace-reason" maxlength="2000" required></textarea>')+
      label('unresolved','<textarea id="workspace-open-questions" rows="2" maxlength="10000"></textarea>')+
      `<button id="workspace-check" class="outline" type="button">${esc(t('preview'))}</button><div id="workspace-preview" aria-live="polite"></div>`+
      checkbox('workspace-approve','approve')+button('workspace-save','save')+'</form></details>'+
      `<details data-workspace-section="evidence"><summary>${esc(t('evidence'))}</summary><p>${esc(t('evidenceNote'))}</p><form id="workspace-upload-form">`+
      label('file',input('workspace-file','type="file" accept="image/png,image/jpeg,application/pdf,text/plain" required'))+
      label('description','<textarea id="workspace-file-description" maxlength="2000" required></textarea>')+
      `<label>${input('workspace-fictional','type="checkbox"')} ${esc(t('fictional'))}</label>`+checkbox('workspace-store','store')+button('workspace-upload','upload')+
      `</form><ul id="workspace-sources"></ul><form id="workspace-fact-form">`+
      label('source',`<select id="workspace-fact-source">${sourceOptions()}</select>`)+
      label('fact',`<select id="workspace-fact">${['rate_per_unit','units_worked','payment_amount','workplace_location','employer_name','other'].map(k=>option(k,({rate_per_unit:t('rate'),units_worked:t('units'),payment_amount:t('amount'),workplace_location:lang==='hi'?'काम की जगह':'Workplace',employer_name:lang==='hi'?'मालिक':'Employer',other:lang==='hi'?'अन्य':'Other'})[k])).join('')}</select>`)+
      label('value','<textarea id="workspace-fact-value" maxlength="2000" required></textarea>')+
      label('unresolved','<textarea id="workspace-fact-unresolved" maxlength="2000"></textarea>')+
      `<label>${input('workspace-fact-confirmed','type="checkbox"')} ${esc(t('factConfirm'))}</label>`+button('workspace-link','link')+`</form><p>${esc(t('noteOnly'))}</p></details>`+
      `<details data-workspace-section="facts"><summary>${esc(t('facts'))}</summary><div id="workspace-facts"></div></details>`+
      `<details data-workspace-section="followup"><summary>${esc(t('followup'))}</summary><p>${esc(t('reminderNote'))}</p><form id="workspace-reminder-form">`+
      label('when',input('workspace-due','type="datetime-local" required'))+
      label('action','<textarea id="workspace-reminder-action" maxlength="1000" required></textarea>')+checkbox('workspace-reminder-consent','consent')+button('workspace-remind','remind')+
      '</form><ul id="workspace-reminders"></ul><form id="workspace-followup-form">'+
      label('reminder',`<select id="workspace-reminder-id">${option('',t('none'))+data.workspace.reminders.filter(r=>r.state==='pending').map(r=>option(r.reminder_id,r.action)).join('')}</select>`)+
      label('outcome',`<select id="workspace-outcome">${option('received',t('newPayment'))+option('none',t('noPayment'))}</select>`)+
      `<div id="workspace-follow-money">${label('amount',input('workspace-new-amount','type="number" min="0.01" step="0.01" required'))+label('date',input('workspace-new-date','type="date"'))+
      label('method',`<select id="workspace-new-method">${option('unknown',t('methodUnknown'))+option('cash',t('cash'))+option('transfer',t('transfer'))}</select>`)}</div>`+
      label('followStatement','<textarea id="workspace-follow-statement" maxlength="2000" required></textarea>')+
      checkbox('workspace-follow-confirm','followConfirm')+`<label>${input('workspace-distinct','type="checkbox"')} ${esc(t('distinct'))}</label>`+button('workspace-record','record')+'</form></details>'+
      `<details data-workspace-section="history"><summary>${esc(t('timeline'))}</summary><ol id="workspace-timeline"></ol></details>`+
      `<a class="workspace-download" href="/worker/workspace/packet">${esc(t('packet'))}</a><p>${esc(t('packetNote'))}</p><p id="workspace-message" role="status" hidden></p></details>`;
    if(!existing)$('case-screen').append(section);
    const r=data.workspace.reconstruction||data.intake;
    $('workspace-basis').value=r.pay_basis;$('workspace-units').value=r.units_worked;$('workspace-rate').value=r.rate_per_unit;
    $('workspace-rate-source').value=r.fact_sources?.rate_per_unit?.[0]||'worker_account';
    $('workspace-units-source').value=r.fact_sources?.units_worked?.[0]||'worker_account';
    $('workspace-open-questions').value=(r.unresolved_questions||[]).join('\n');
    if(r.payments)r.payments.forEach(paymentRow);
    else if(Number(data.intake.payments_received)>0)paymentRow({payment_id:'initial-received',amount:data.intake.payments_received,status:'received',allocation:'this_case',worker_confirmed:true,statement:data.intake.original_statement});
    $('workspace-save').disabled=true;
    $('workspace-add').onclick=()=>{paymentRow();invalidate();};
    $('workspace-reconstruction-form').addEventListener('input',event=>{if(event.target.id!=='workspace-approve')invalidate();});
    $('workspace-check').onclick=()=>action($('workspace-reconstruction-form'),async()=>{
      const form=$('workspace-reconstruction-form');
      // Preview does not require the final approval checkbox.
      const required=$('workspace-approve').required;$('workspace-approve').required=false;
      const valid=form.reportValidity();$('workspace-approve').required=required;if(!valid)return;
      const body=snapshot(),result=await api('/worker/workspace/preview',body);
      if(result.version!==record.workspace.version)throw new Error(t('reload'));
      checkedSnapshot=JSON.stringify(body);checkedVersion=result.version;$('workspace-preview').innerHTML=summary(result.calculation);
    });
    $('workspace-reconstruction-form').onsubmit=event=>{event.preventDefault();action(event.currentTarget,async()=>{
      const body=snapshot();if(checkedSnapshot!==JSON.stringify(body))throw new Error(t('needPreview'));
      const request={expected_version:checkedVersion,reconstruction:body,reason:$('workspace-reason').value,worker_confirmed:$('workspace-approve').checked};
      const result=await api('/worker/workspace/reconstruction',{...request,operation_id:op('revision',request)});
      document.activeElement?.blur();refreshCase(result);
    });};
    $('workspace-sources').innerHTML=data.workspace.sources.length?data.workspace.sources.map(s=>`<li><a href="/worker/workspace/evidence/${esc(s.source_id)}">${esc(s.filename)}</a> ${s.fictional?'[DEMO]':''}<br><small>${esc(s.description)}</small></li>`).join(''):`<li>${esc(t('empty'))}</li>`;
    $('workspace-upload-form').onsubmit=event=>{event.preventDefault();action(event.currentTarget,async()=>{
      const file=$('workspace-file').files[0];if(!file||file.size>5*1024*1024)throw new Error(t('file'));
      const content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=reject;reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(file);});
      const body={filename:file.name,mime:file.type||'text/plain',content_base64:content,description:$('workspace-file-description').value,fictional:$('workspace-fictional').checked,consent_to_store:$('workspace-store').checked};
      const result=await api('/worker/workspace/evidence',{...body,operation_id:op('upload',body)});document.activeElement?.blur();refreshCase(result.case);
    });};
    $('workspace-fact-form').onsubmit=event=>{event.preventDefault();action(event.currentTarget,async()=>{
      const body={source_id:$('workspace-fact-source').value,fact:$('workspace-fact').value,value:$('workspace-fact-value').value,unresolved:$('workspace-fact-unresolved').value,worker_confirmed:$('workspace-fact-confirmed').checked};
      const result=await api('/worker/workspace/fact-source',{...body,operation_id:op('fact',body)});document.activeElement?.blur();refreshCase(result);
    });};
    $('workspace-facts').innerHTML='<table><thead><tr>'+['fact','value','source','unresolved'].map(k=>`<th>${esc(t(k))}</th>`).join('')+'</tr></thead><tbody>'+data.workspace.facts.map(f=>`<tr><td>${esc(factLabel(f.fact))}</td><td>${esc(f.value)}</td><td>${esc((f.source_ids||[f.source_id||'worker_account']).map(sourceLabel).join(', '))}</td><td>${esc(f.unresolved)}</td></tr>`).join('')+'</tbody></table>';
    $('workspace-reminders').innerHTML=data.workspace.reminders.map(r=>`<li><strong>${esc(t(r.state==='completed'?'completed':r.due?'due':'pending'))}</strong> · ${esc(new Date(r.due_at).toLocaleString(lang==='hi'?'hi-IN':'en-IN'))} · ${esc(r.action)}</li>`).join('');
    $('workspace-reminder-form').onsubmit=event=>{event.preventDefault();action(event.currentTarget,async()=>{
      const body={due_at:new Date($('workspace-due').value).toISOString(),action:$('workspace-reminder-action').value,consent:$('workspace-reminder-consent').checked};
      const result=await api('/worker/workspace/reminders',{...body,operation_id:op('reminder',body)});document.activeElement?.blur();refreshCase(result);
    });};
    $('workspace-outcome').onchange=()=>{const none=$('workspace-outcome').value==='none';$('workspace-follow-money').hidden=none;$('workspace-new-amount').required=!none;};
    $('workspace-followup-form').onsubmit=event=>{event.preventDefault();action(event.currentTarget,async()=>{
      const received=$('workspace-outcome').value==='received',reminder_id=$('workspace-reminder-id').value||null;
      const body=received?{amount:$('workspace-new-amount').value,received_on:$('workspace-new-date').value||null,method:$('workspace-new-method').value,original_statement:$('workspace-follow-statement').value,worker_confirmed:$('workspace-follow-confirm').checked,distinct_payment_confirmed:$('workspace-distinct').checked,reminder_id}:
        {statement:$('workspace-follow-statement').value,worker_confirmed:$('workspace-follow-confirm').checked,reminder_id};
      const result=await api(received?'/worker/payments':'/worker/workspace/no-payment-followup',{...body,operation_id:op('followup',body)});document.activeElement?.blur();refreshCase(received?result.case:result);
    });};
    $('workspace-timeline').innerHTML=data.workspace.timeline.map(e=>`<li>${esc(new Date(e.at).toLocaleString(lang==='hi'?'hi-IN':'en-IN'))} · ${esc(e.description)}</li>`).join('');
    if(changingLanguage){
      $('workspace-payments').replaceChildren();rows.forEach(paymentRow);
      for(const edit of edits){const n=$(edit.id);if(!n)continue;if(edit.type==='file'){try{n.files=edit.files;}catch{}}else if(edit.type==='checkbox')n.checked=edit.checked;else n.value=edit.value;}
      Array.from(section.querySelectorAll('details')).forEach((n,i)=>n.open=!!opened[i]);
      // A corrected calculation still needs its explicit preview/approval after rebuilding.
      invalidate();
    }


    window.HaqSectionVoice?.mount(section,{
      payments:()=>snapshot().payments,
      setPayments:rows=>{$('workspace-payments').replaceChildren();for(const payment of rows){const original=payment.source_ids||['worker_account'];paymentRow({...payment,source_ids:payment.source_id&&payment.source_id!==original[0]?[payment.source_id]:original});}invalidate();},
      invalidate
    });
  }
  window.addEventListener('haqrecord-case',event=>render(event.detail));
  window.addEventListener('haqrecord-calculation',event=>{
    let box=$('voice-allocation-summary');if(!box){box=document.createElement('div');box.id='voice-allocation-summary';$('draft-review').insertBefore(box,$('approve-voice-form'));}
    lang=document.documentElement.lang==='en'?'en':'hi';
    box.innerHTML=event.detail.payment_items?summary(event.detail):'';
  });
})();
