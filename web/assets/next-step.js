/* Practical help after intake; external links are displayed, never auto-spoken. */
(() => {
  const text={
    en:{summary:'Your account for asking for help',say:'What you can say',bring:'Useful records, if you have them',contact:'Published general contact',
        open:'Open official information',call:'Call published contact',read:'Hear my summary',download:'Download my help summary',
        city:'Where was the workplace?',choose:'Choose a city',confirm:'Confirm this is where I worked',error:'Unable to load this step. Try opening your case again.',
        note:'This is your reported account, not a legal finding. Nothing has been submitted to a government office.',follow:'Continue the same case'},
    hi:{summary:'मदद मांगने के लिए आपकी बात का सार',say:'आप क्या कह सकते हैं',bring:'अगर हों तो ये रिकॉर्ड साथ रखें',contact:'प्रकाशित सामान्य संपर्क',
        open:'आधिकारिक जानकारी खोलें',call:'प्रकाशित संपर्क पर कॉल करें',read:'मेरा सार सुनाएं',download:'मदद के लिए सार डाउनलोड करें',
        city:'काम की जगह किस शहर में थी?',choose:'शहर चुनें',confirm:'पुष्टि करें: मैंने इसी शहर में काम किया',error:'यह जानकारी नहीं खुल सकी। अपना मामला फिर खोलें।',
        note:'यह आपकी बताई जानकारी है, कानूनी फैसला नहीं। सरकारी कार्यालय में कुछ नहीं भेजा गया है।',follow:'इसी मामले को आगे अपडेट करें'},
  };
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let sequence=0,lastSavedKey='';
  function render(step,host,id,language){
    const t=text[language],card=document.getElementById(id)||document.createElement('section');
    const payload=JSON.stringify([step,language]);if(card.dataset.payload===payload)return;card.dataset.payload=payload;
    card.id=id;card.className='worker-next-step';
    let html=`<h2>${esc(step.title)}</h2>`;
    if(step.summary)html+=`<h3>${esc(t.summary)}</h3><p>${esc(step.summary)}</p><p class="quiet-note">${esc(t.note)}</p>`;
    if(['clarify','review_balance','balance_settled'].includes(step.kind))html+=`<p class="next-question">${esc(step.next_question)}</p>`;
    if(step.kind==='confirm_city')html+=`<form class="next-step-city"><label>${esc(t.city)}<select required><option value="">${esc(t.choose)}</option><option value="hyderabad">Hyderabad / हैदराबाद</option><option value="bengaluru">Bengaluru / बेंगलुरु</option></select></label><button class="outline" type="submit">${esc(t.confirm)}</button><p role="status"></p></form>`;
    const r=step.resource_card;
    if(r){
      html+=`<h3>${esc(r.display_name)}</h3><p>${esc(r.action)}</p><h4>${esc(t.say)}</h4><p>${esc(r.what_to_say)}</p><h4>${esc(t.bring)}</h4><ul>${r.bring.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`+
        `<p>${esc(t.contact)}: ${esc(r.phone)}<br>${esc(r.address)}</p><div class="next-step-actions"><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(t.open)}</a><a href="tel:${esc(r.phone.replace(/[^+\d]/g,''))}">${esc(t.call)}</a></div><p class="quiet-note">${esc(r.notice)}</p>`;
    }
    if(step.case_id&&step.summary)html+=`<div class="next-step-actions"><button class="text-button next-step-read" type="button">${esc(t.read)}</button><a href="/worker/workspace/help-summary?language=${language}">${esc(t.download)}</a></div>`;
    if(step.follow_up)html+=`<h3>${esc(t.follow)}</h3><p>${esc(step.follow_up)}</p>`;
    const expanded=card.querySelector('details')?.open;card.innerHTML=id==='case-next-step'?`<details ${expanded?'open':''}><summary>${esc(language==='hi'?'कहाँ मदद मिल सकती है?':'Where can I get help?')}</summary>${html}</details>`:html;if(!card.parentNode)host.append(card);
    const read=card.querySelector('.next-step-read');if(read)read.onclick=()=>speak(step.summary);
    const cityForm=card.querySelector('.next-step-city');
    if(cityForm){
      let operation=null,chosen='';
      cityForm.onsubmit=async event=>{
        event.preventDefault();const button=cityForm.querySelector('button'),status=cityForm.querySelector('[role=status]');button.disabled=true;
        try{
          const city=cityForm.querySelector('select').value;if(!city)return;
          if(chosen!==city){chosen=city;operation=crypto.randomUUID();}
          const sessionResponse=await fetch('/worker/session');if(!sessionResponse.ok)throw new Error(t.error);
          const session=await sessionResponse.json();
          const response=await fetch('/worker/workspace/fact-source',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},
            body:JSON.stringify({operation_id:operation,source_id:'worker_account',fact:'workplace_location',value:city==='hyderabad'?'Hyderabad':'Bengaluru',unresolved:'',worker_confirmed:true})});
          const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:t.error);
          renderCase(data);
        }catch(error){status.textContent=error.message;}finally{button.disabled=false;}
      };
    }
  }
  window.addEventListener('haqrecord-case',async event=>{if(event.detail.record_type==='work_diary'&&!event.detail.workspace.reconstruction){document.getElementById('case-next-step')?.remove();return;}
    const request=++sequence,language=document.documentElement.lang==='en'?'en':'hi';
    try{
      const response=await fetch('/worker/workspace/next-step?language='+language);if(!response.ok)return;
      const step=await response.json();if(request!==sequence)return;
      render(step,document.getElementById('case-screen'),'case-next-step',language);
    }catch{/* The saved case remains usable if the optional help card cannot load. */}
  });
  window.addEventListener('haqrecord-next-step',event=>{
    const host=document.getElementById('voice-screen');if(!host)return;
    if(!event.detail){sequence++;lastSavedKey='';document.getElementById('voice-next-step')?.remove();return;}
    render(event.detail,host,'voice-next-step',document.documentElement.lang==='en'?'en':'hi');
  });
  window.addEventListener('haqrecord-case-saved',async event=>{
    const language=document.documentElement.lang==='en'?'en':'hi',key=JSON.stringify([event.detail,language]);
    if(key===lastSavedKey&&document.getElementById('voice-next-step'))return;
    lastSavedKey=key;const request=++sequence;
    try{
      const response=await fetch('/worker/workspace/next-step?language='+language);if(!response.ok){lastSavedKey='';return;}
      const step=await response.json();if(request!==sequence)return;
      render(step,document.getElementById('voice-screen'),'voice-next-step',language);
    }catch{lastSavedKey='';}
  });
  window.addEventListener('haqrecord-resources',event=>{
    const card=event.detail.action_card;if(!card)return;
    render({title:card.title,resource_card:card},document.getElementById('voice-screen'),'voice-next-step',document.documentElement.lang==='en'?'en':'hi');
  });
})();
