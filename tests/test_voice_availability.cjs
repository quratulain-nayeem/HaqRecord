const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../web/assets/worker-flow.js'),'utf8');
const section=source.slice(source.indexOf('let checkingVoiceAvailability='),source.indexOf('\nObject.assign(words.hi,{voiceSettingsAdvisory:'));
const message={textContent:'serviceUnavailable'};
let requests=0,result={ready:true,backend_connected:true};
const context={busy:false,voiceReady:false,currentScreen:'voice',voiceConfigurationStatus:'',voiceConfigurationWarnings:[],
  $:()=>message,t:key=>key,updateCall:()=>{},notify:(_,text)=>{message.textContent=text;},
  api:async()=>{requests++;return result;}};
vm.createContext(context);vm.runInContext(section,context);
(async()=>{
  await context.refreshVoiceAvailability();
  assert.equal(context.voiceReady,true);assert.equal(message.textContent,'');
  result={ready:true,backend_connected:false};
  await context.refreshVoiceAvailability();
  assert.equal(context.voiceReady,false);assert.equal(message.textContent,'serviceUnavailable');
  message.textContent='micDenied';result={ready:true,backend_connected:true};
  await context.refreshVoiceAvailability();assert.equal(message.textContent,'micDenied');
  context.busy=true;const before=requests;await context.refreshVoiceAvailability();assert.equal(requests,before);
  context.busy=false;let resolve;
  context.api=()=>{requests++;return new Promise(done=>{resolve=done;});};
  const pending=context.refreshVoiceAvailability();await context.refreshVoiceAvailability();assert.equal(requests,before+1);
  message.textContent='new call error';resolve(result);await pending;assert.equal(message.textContent,'new call error');
  context.api=async()=>{throw new Error('offline');};message.textContent='';
  await context.refreshVoiceAvailability();assert.equal(context.voiceReady,false);assert.equal(message.textContent,'serviceUnavailable');
  console.log('PASS: voice readiness recovers, detects outages, preserves errors, and skips active calls and overlapping checks.');
})().catch(error=>{console.error(error);process.exitCode=1;});
