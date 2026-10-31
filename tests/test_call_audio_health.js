const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
let tick,cleared=0;
const context=vm.createContext({window:{},setInterval(fn){tick=fn;return 1;},clearInterval(){cleared++;}});
vm.runInContext(fs.readFileSync('web/assets/call-audio-health.js','utf8'),context);
const health=context.window.HaqCallAudio;
const report=(bytes,packets)=>new Map([
  ['audio',{type:'outbound-rtp',kind:'audio',bytesSent:bytes,packetsSent:packets}],
  ['video',{type:'outbound-rtp',kind:'video',bytesSent:99999,packetsSent:99999}],
  ['received',{type:'inbound-rtp',kind:'audio',bytesSent:99999,packetsSent:99999}]
]);
assert.equal(health.inspect(report(20,2),null).sending,null);
assert.equal(health.inspect(report(40,4),{bytes:20,packets:2}).sending,true);
assert.equal(health.inspect(report(40,4),{bytes:40,packets:4}).sending,false);
(async()=>{
  const states=[];
  const track={kind:'audio',readyState:'live',enabled:true,muted:false};
  let bytes=20;
  const pc={getSenders:()=>[{track}],getStats:async()=>report(bytes,bytes/10)};
  const call={peerConnection:()=>pc};
  const stop=health.watch(call,s=>states.push(s.state));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(states.at(-1),'checking');
  bytes=40;await tick();assert.equal(states.at(-1),'sending');
  await tick();assert.equal(states.at(-1),'stalled');
  track.muted=true;await tick();assert.equal(states.at(-1),'muted');
  track.muted=false;pc.getSenders=()=>[];await tick();assert.equal(states.at(-1),'missing');
  stop();const count=states.length;await tick();assert.equal(states.length,count);assert.equal(cleared,1);
  console.log('PASS: outgoing audio checked independently of incoming playback/video; stalled, muted and missing tracks detected; monitoring stops cleanly.');
})().catch(e=>{console.error(e);process.exitCode=1;});
