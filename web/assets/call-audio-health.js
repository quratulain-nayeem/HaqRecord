/* Metadata only: no audio recording, transcript capture or uploads. */
(() => {
  function audioTracks(call) {
    return (call?.peerConnection?.()?.getSenders?.() || [])
      .map(sender => sender.track).filter(track => track?.kind === 'audio');
  }
  function inspect(report, previous) {
    let bytes=0, packets=0;
    report.forEach(item => {
      if(item.type==='outbound-rtp'&&(item.kind==='audio'||item.mediaType==='audio')) {
        bytes+=item.bytesSent||0;packets+=item.packetsSent||0;
      }
    });
    return {bytes,packets,sending:previous ? bytes>previous.bytes&&packets>previous.packets : null};
  }
  function watch(call, onUpdate) {
    let stopped=false, previous=null, pending=false;
    const sample=async()=>{
      if(stopped||pending)return;
      pending=true;
      try {
        const pc=call?.peerConnection?.();
        const tracks=audioTracks(call);
        if(!pc||!tracks.length){onUpdate({state:'missing'});return;}
        if(tracks.every(track=>track.readyState==='ended'||!track.enabled||track.muted)) {
          onUpdate({state:'muted'});return;
        }
        const current=inspect(await pc.getStats(),previous);
        if(stopped)return;
        previous=current;
        onUpdate({...current,state:current.sending===null?'checking':current.sending?'sending':'stalled'});
      } catch {if(!stopped)onUpdate({state:'unknown'});}
      finally {pending=false;}
    };
    const timer=setInterval(sample,1500);sample();
    return ()=>{stopped=true;clearInterval(timer);};
  }
  window.HaqCallAudio={audioTracks,inspect,watch};
})();
