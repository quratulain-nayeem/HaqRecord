const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').join(__dirname,'../web/assets/worker-flow.js'),'utf8');
const errorFunction=source.slice(source.indexOf('function humanError(error){'),source.indexOf('\nasync function api('));
const launchFunction=source.slice(source.indexOf('async function launchCall(){'),source.indexOf('\nfunction balanceSpeech('));
const messages=[],elements={};let constructorCalls=0,fetchCalls=0,stoppedTracks=0;
const context={t:key=>key,currentScreen:'voice',busy:false,voiceReady:true,voiceCsrf:'',voiceMode:'new',workerSession:null,language:'en',
 window:{isSecureContext:true,dispatchEvent(){}},CustomEvent:class {constructor(type,options){this.type=type;this.detail=options.detail;}},navigator:{mediaDevices:{getUserMedia:async()=>{const error=new Error('missing');error.name='NotFoundError';throw error;}}},
 $:id=>elements[id]??=(id==='voice-consent'?{checked:true}:{}),
 notify:(id,message)=>messages.push(message),updateCall:()=>{},stopMicrophoneCheck:async()=>{},microphoneConstraints:()=>({echoCancellation:true}),
 BolnaWebCall:class {constructor(options){constructorCalls++;this.options=options;}on(){}async start(){await this.options.getSession();const e=new Error('SDK wrapped quota');e.code='mint_failed';e.cause2={status:429,code:'voice_daily_limit'};throw e;}async stop(){}},
 fetch:async()=>{fetchCalls++;return {ok:true,json:async()=>({run_id:'fictional'}),headers:{get:()=> 'fixture-csrf'}};},
};
vm.createContext(context);vm.runInContext(errorFunction+'\n'+launchFunction,context);
assert.equal(context.humanError({code:'mint_failed',cause2:{status:429,code:'voice_daily_limit'}}),'tooMany');
assert.equal(context.humanError({code:'mint_failed',cause:{status:503,code:'voice_configuration_changed'}}),'settingsChanged');
assert.equal(context.humanError({code:'microphone_denied',cause2:{name:'NotFoundError'}}),'micUnavailable');
assert.equal(context.humanError({code:'connect_failed'}),'voiceConnectFailed');
assert.equal(context.humanError({code:'mint_failed',cause2:{status:502}}),'voiceProviderError');
assert.equal(context.humanError({code:'microphone_denied',cause:{name:'NotReadableError'}}),'micBusy');
(async()=>{
 await context.launchCall();assert.equal(constructorCalls,0);assert.equal(fetchCalls,0);assert.equal(context.busy,false);assert.equal(messages.at(-1),'micUnavailable');
 context.navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop:()=>stoppedTracks++}]});
 await context.launchCall();assert.equal(constructorCalls,1);assert.equal(fetchCalls,1);assert.equal(stoppedTracks,1);assert.equal(messages.at(-1),'tooMany');
 console.log('PASS: SDK cause and cause2 preserve actual errors; no session is requested when the microphone fails; successful preflight closes the probe; provider throttling is never mislabeled as internet failure.');
})().catch(error=>{console.error(error);process.exitCode=1;});
