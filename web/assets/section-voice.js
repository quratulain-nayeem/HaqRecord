/* A real Bolna call for one workspace block; never submits the form. */
(() => {
  const drafts=new Map();let host=null,adapter=null,session=null,timer=null,starting=false,stopping=false,sequence=0,caseId=null;
  const t=(en,hi)=>document.documentElement.lang==='hi'?hi:en;
  const get=id=>document.getElementById(id);
  const titles={agreement:['agreement and payments','समझौता और भुगतान'],evidence:['supporting material and facts','कागज़ और जानकारी'],facts:['facts and their sources','जानकारी और स्रोत'],followup:['follow-up','आगे की बात'],history:['case history','मामले का इतिहास']};
  function box(key){return host?.querySelector(`[data-workspace-section="${key}"] .section-voice`);}
  function note(key,value,error=false){const n=box(key)?.querySelector('[data-section-status]');if(n){n.textContent=value;n.classList.toggle('error',error);}}
  function controls(key){const root=box(key);if(!root)return;const running=session?.key===key&&!session.paused;
    root.querySelector('[data-section-start]').hidden=!!running;
    root.querySelector('[data-section-pause]').hidden=!running;
    root.querySelector('[data-section-end]').hidden=!running;
    root.querySelector('[data-section-restart]').hidden=!drafts.has(key);
    root.querySelector('[data-section-start]').disabled=starting||!!running;
    root.querySelector('[data-section-pause]').disabled=starting||stopping;
    root.querySelector('[data-section-start]').textContent=drafts.has(key)?t('Continue with Sara','सारा से आगे बात करें'):
      ['facts','history'].includes(key)?t('🎙 Ask Sara about these records','🎙 इन रिकॉर्ड के बारे में सारा से पूछें'):t('🎙 Answer with Sara','🎙 सारा को बोलकर बताएं');
    root.querySelector('[data-section-pause]').textContent=t('Pause','रोकें');
    root.querySelector('[data-section-restart]').textContent=t('Start this section again','यह भाग फिर शुरू करें');
    root.querySelector('[data-section-end]').textContent=t('Finish talking','बात खत्म करें');
  }
  function collect(key){
    const values={};const block=host.querySelector(`[data-workspace-section="${key}"]`);
    block.querySelectorAll('input[id],textarea[id],select[id]').forEach(node=>{
      if(node.id==='workspace-approve')return; // Private final approval is never filled by voice.
      values[node.id]=node.type==='checkbox'?node.checked:node.type==='file'?(node.files[0]?.name||''):node.value;
    });
    if(key==='agreement')values._payments=adapter.payments();
    return values;
  }
  function apply(state){
    if(!host||!state)return;
    const draft=drafts.get(state.section);if(!draft)return;
    if(draft.lastRevision===state.revision)return;
    for(const [key,value] of Object.entries(state.values)){
      if(key==='_payments'){
        if(JSON.stringify(draft.applied?._payments)!==JSON.stringify(value))adapter.setPayments(value);
        continue;
      }
      if(key==='workspace-file'||key==='workspace-approve'||draft.applied?.[key]===value)continue;
      const node=get(key);if(!node||!host.querySelector(`[data-workspace-section="${state.section}"]`)?.contains(node))continue;
      if(node.type==='checkbox')node.checked=value===true;else node.value=value??'';
      node.dispatchEvent(new Event('input',{bubbles:true}));node.dispatchEvent(new Event('change',{bubbles:true}));
    }
    draft.applied=structuredClone(state.values);draft.lastRevision=state.revision;
    if(state.section==='agreement')adapter.invalidate();
    const question=box(state.section)?.querySelector('[data-section-question]');
    if(question)question.textContent=state.next_question|| (state.read_only?t('Ask Sara about the records in this block.','इस भाग के रिकॉर्ड के बारे में सारा से पूछें।'):t('Answers filled. Check this block before saving.','जवाब भर गए। सहेजने से पहले यह भाग जांचें।'));
    if(state.status==='questions_complete')note(state.section,t('Nothing is saved yet. Use this block’s check and save buttons.','अभी कुछ सहेजा नहीं गया है। इसी भाग के जांचने और सहेजने के बटन इस्तेमाल करें।'));
  }
  async function state(){if(!session)return;const current=session;
    try{const response=await fetch('/voice/intake/section-state');if(!response.ok)return;const data=await response.json();if(session===current&&data.section===current.key)apply(data);}catch{/* A transient poll must not end the call or erase typed answers. */}
  }
  async function revoke(csrf){if(!csrf)return;try{await fetch('/voice/intake/end',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf}});}catch{}}
  async function pause(finish=false){
    if(!session||session.paused||stopping)return;stopping=true;const current=session;current.paused=true;
    clearInterval(timer);timer=null;
    await revoke(current.csrf);
    try{await current.call?.stop();}catch{}
    if(session===current){busy=false;callState='ended';await state();controls(current.key);
      note(current.key,finish?t('Voice stopped. Check your answers before saving.','बात बंद है। सहेजने से पहले जवाब जांचें।'):t('Paused. Your answers are kept. Press Continue when ready.','रुक गई। जवाब यहीं हैं। तैयार हों तो आगे बात करें दबाएं।'));}
    stopping=false;
  }
  async function begin(key,restart=false){
    if(starting||stopping)return;
    if(session&&!session.paused){if(session.key!==key){note(key,t('Pause the other conversation first.','पहले दूसरी बातचीत रोकें।'),true);return;}await pause();}
    if(typeof busy!=='undefined'&&busy){note(key,t('End the other conversation first.','पहले दूसरी बातचीत खत्म करें।'),true);return;}
    const root=box(key),consent=root.querySelector('[data-section-consent]');root.querySelector('[data-section-setup]').hidden=false;
    if(!consent.checked){note(key,t('Allow voice use, then press the microphone.','आवाज़ इस्तेमाल करने की अनुमति दें, फिर माइक दबाएं।'));consent.focus();return;}
    if(!window.isSecureContext||typeof BolnaWebCall==='undefined'){note(key,t('Voice is unavailable. You can still fill these fields.','आवाज़ से बात अभी नहीं हो सकती। आप नीचे लिख सकते हैं।'),true);return;}
    starting=true;const ticket=++sequence;note(key,t('Connecting…','जोड़ रहे हैं…'));controls(key);
    const language=document.documentElement.lang==='hi'?'hi':'en';
    try{
      const probe=await navigator.mediaDevices.getUserMedia({audio:microphoneConstraints(),video:false});probe.getTracks().forEach(track=>track.stop());
      window.HaqReadAloud?.stop();
      const draft=drafts.get(key)||{initial:collect(key),applied:null,lastRevision:-1};drafts.set(key,draft);
      if(restart){draft.applied=null;draft.lastRevision=-1;}
      const values=restart?structuredClone(draft.initial):collect(key);
      if(key==='evidence')values['workspace-file']=collect(key)['workspace-file'];
      const current={key,language,paused:false,csrf:'',call:null};session=current;busy=true;
      const sdk=new BolnaWebCall({audio:microphoneConstraints(),getSession:async()=>{
        const response=await fetch('/voice/intake/session',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':workerSession.csrf_token},
          body:JSON.stringify({consent_to_voice_processing:true,mode:'existing',language,section:key,section_values:values,restart_section:restart})});
        const payload=await response.json();if(!response.ok){const error=new Error(typeof payload.detail==='string'?payload.detail:payload.detail?.message||'Voice could not connect.');error.status=response.status;throw error;}
        current.csrf=response.headers.get('X-Voice-CSRF')||'';voiceCsrf=current.csrf;return payload;
      }});current.call=sdk;call=sdk;
      sdk.on('call-start',()=>{if(session!==current)return;note(key,t('Sara is listening. Only this block will be filled.','सारा सुन रही है। सिर्फ़ यही भाग भरेगा।'));controls(key);state();timer=setInterval(state,1000);});
      sdk.on('call-end',()=>{if(session!==current||current.paused)return;current.paused=true;busy=false;clearInterval(timer);timer=null;revoke(current.csrf);state();controls(key);note(key,t('Conversation stopped. Your draft answers are kept.','बात रुक गई। आपके जवाब यहीं हैं।'));});
      sdk.on('error',error=>{if(session===current)note(key,humanError(error),true);});
      await sdk.start();if(ticket!==sequence){await sdk.stop();return;}await state();
    }catch(error){busy=false;if(session?.key===key){session.paused=true;await revoke(session.csrf);try{await session.call?.stop();}catch{}}
      note(key,typeof humanError==='function'?humanError(error):error.message,true);
    }finally{starting=false;controls(key);}
  }
  function mount(section,newAdapter){
    // A case refresh must not replace in-progress voice answers with saved values.
    const changedCase=caseId&&caseId!==section.dataset.caseId;
    if(changedCase){pause(true);drafts.clear();}
    host=section;adapter=newAdapter;caseId=section.dataset.caseId;
    section.querySelectorAll('[data-workspace-section]').forEach(block=>{
      const key=block.dataset.workspaceSection;if(block.querySelector('.section-voice'))return;
      const root=document.createElement('div');root.className='section-voice';
      const start=document.createElement('button');start.type='button';start.className='outline section-microphone';start.dataset.sectionStart='';
      start.setAttribute('aria-label',t('Speak with Sara about ','इस भाग के बारे में सारा से बात करें: ')+titles[key][document.documentElement.lang==='hi'?1:0]);
      const setup=document.createElement('div');setup.dataset.sectionSetup='';setup.hidden=true;
      const label=document.createElement('label'),consent=document.createElement('input');consent.type='checkbox';consent.dataset.sectionConsent='';
      consent.checked=drafts.has(key);label.append(consent,document.createTextNode(t(' I allow this AI voice conversation.',' मैं AI से आवाज़ में बात करने की अनुमति देता/देती हूँ।')));setup.append(label);
      const row=document.createElement('div');row.className='section-voice-controls';
      for(const action of ['pause','restart','end']){const button=document.createElement('button');button.type='button';button.dataset['section'+action[0].toUpperCase()+action.slice(1)]='';row.append(button);}
      const question=document.createElement('p');question.dataset.sectionQuestion='';question.className='section-question';
      const status=document.createElement('p');status.dataset.sectionStatus='';status.setAttribute('role','status');
      root.append(start,setup,row,question,status);block.querySelector('summary').after(root);
      start.onclick=()=>begin(key);row.querySelector('[data-section-pause]').onclick=()=>pause();row.querySelector('[data-section-end]').onclick=()=>pause(true);
      row.querySelector('[data-section-restart]').onclick=()=>begin(key,true);controls(key);
      if(drafts.has(key)){drafts.get(key).lastRevision=-1;if(session?.key===key)state();}
    });
  }
  document.addEventListener('change',async event=>{
    if(event.target.id!=='workspace-file'||session?.key!=='evidence')return;
    try{await fetch('/voice/intake/section-file',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf},body:JSON.stringify({filename:event.target.files[0]?.name||''})});
      note('evidence',t('File selected on screen. Tell Sara “done” to continue. It is not uploaded yet.','फ़ाइल चुनी गई। आगे बढ़ने के लिए सारा से कहें “हो गया”। अभी अपलोड नहीं हुई है।'));}catch{}
  });
  window.addEventListener('pagehide',()=>{clearInterval(timer);session?.call?.stop();});
  window.HaqSectionVoice={mount,pause};
})();
