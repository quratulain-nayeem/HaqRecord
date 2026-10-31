/* Shared controls for page help and summaries; never controls the live call. */
(() => {
  let last='', language='hi', generation=0, playing=false, paused=false;
  const synth=window.speechSynthesis;
  const words={en:{pause:'Pause',resume:'Continue listening',restart:'Start again',stop:'Stop',label:'Listening controls'},
    hi:{pause:'रोकें',resume:'आगे सुनें',restart:'फिर से सुनें',stop:'बंद करें',label:'सुनने के बटन'}};
  const get=id=>document.getElementById(id);
  function sync(){
    const t=words[document.documentElement.lang==='en'?'en':'hi'];
    const box=get('reading-controls');if(!box)return;
    box.hidden=!playing;box.setAttribute('aria-label',t.label);
    get('reading-pause').textContent=paused?'▶ '+t.resume:'Ⅱ '+t.pause;
    get('reading-pause').setAttribute('aria-pressed',String(paused));
    get('reading-restart').textContent='↻ '+t.restart;get('reading-stop').textContent='■ '+t.stop;
  }
  function stop(){generation++;playing=false;paused=false;if(synth)synth.cancel();sync();}
  function read(value,requestedLanguage){
    stop();last=String(value||'');language=requestedLanguage||document.documentElement.lang;
    if(!synth||!last.trim())return;
    const current=generation;playing=true;sync();
    const chunks=last.match(/[^।.!?]+[।.!?]?/g)||[last];
    chunks.forEach((chunk,index)=>{
      const utterance=new SpeechSynthesisUtterance(chunk);utterance.lang=language==='hi'?'hi-IN':'en-IN';utterance.rate=.9;
      const voice=synth.getVoices().find(v=>v.lang.toLowerCase().startsWith(language));if(voice)utterance.voice=voice;
      utterance.onend=()=>{if(current===generation&&index===chunks.length-1){playing=false;paused=false;sync();}};
      utterance.onerror=()=>{if(current===generation)stop();};synth.speak(utterance);
    });
  }
  window.HaqReadAloud={read,stop};
  document.addEventListener('DOMContentLoaded',()=>{
    get('reading-pause').onclick=()=>{if(!playing)return;paused=!paused;if(paused)synth.pause();else synth.resume();sync();};
    get('reading-restart').onclick=()=>read(last,language);get('reading-stop').onclick=stop;sync();
  });
  window.addEventListener('haqrecord-language',stop);
  window.addEventListener('pagehide',stop);
})();
