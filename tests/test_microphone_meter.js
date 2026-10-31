const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, {
    value: '', hidden: false, checked: false, disabled: false, textContent: '',
    replaceChildren() {}, append() {},
  });
  return nodes.get(id);
};
let amplitude = 0, nextFrame = 0, stoppedTracks = 0, closedContexts = 0;
const frames = new Map();
const stream = () => ({getTracks: () => [{stop() { stoppedTracks++; }}]});
class AudioContext {
  async resume() {}
  async close() { closedContexts++; }
  createMediaStreamSource() { return {connect() {}}; }
  createAnalyser() { return {fftSize: 1024, getFloatTimeDomainData(samples) {
    // Alternating signed samples represent sound without a DC offset.
    for (let i = 0; i < samples.length; i++) samples[i] = i % 2 ? amplitude : -amplitude;
  }}; }
}
const mediaDevices = {
  getUserMedia: async () => stream(),
  enumerateDevices: async () => [{kind: 'audioinput', deviceId: 'test-mic', label: 'Test microphone'}],
};
const context = vm.createContext({
  document: {getElementById: get, createElement: () => ({})},
  localStorage: {getItem: () => 'en'},
  window: {AudioContext, addEventListener() {}},
  navigator: {mediaDevices},
  requestAnimationFrame(callback) { frames.set(++nextFrame, callback); return nextFrame; },
  cancelAnimationFrame(id) { frames.delete(id); },
  setTimeout() { throw new Error('The microphone check must not silently time out'); },
});
const source = fs.readFileSync(path.join(__dirname, '../web/assets/worker-flow.js'), 'utf8');
vm.runInContext(source.replace(/initialize\(\)\.catch\(\(\)=>notify\('page-message',t\('networkError'\)\)\);\s*$/, ''), context);
const run = code => vm.runInContext(code, context);
function frame() {
  const [id, callback] = frames.entries().next().value;
  frames.delete(id); callback();
}
(async () => {
  // Consent is required before acquiring any stream.
  await run('checkMicrophone()');
  assert.equal(run('micCheckActive'), false);
  get('voice-consent').checked = true;
  await run('checkMicrophone()');
  assert.equal(get('microphone-level').hidden, false);
  assert.equal(get('microphone-level').value, 0);
  assert.match(get('check-microphone').textContent, /Stop/);
  amplitude = .01; frame();
  const quietSpeech = get('microphone-level').value;
  assert.ok(quietSpeech > .2 && quietSpeech < 1);
  assert.match(get('microphone-check-status').textContent, /picking up sound/);
  amplitude = .08; frame();
  assert.ok(get('microphone-level').value > quietSpeech);
  amplitude = 0; frame();
  assert.equal(get('microphone-level').value, 0);
  assert.match(get('microphone-check-status').textContent, /Listening for sound/);
  for (let i = 0; i < 700; i++) frame();
  assert.equal(run('micCheckActive'), true);
  await run('checkMicrophone()');
  assert.equal(get('microphone-level').hidden, true);
  assert.equal(get('microphone-level').value, 0);
  assert.equal(frames.size, 0);
  assert.equal(stoppedTracks, 1);
  assert.equal(closedContexts, 1);
  assert.match(get('microphone-check-status').textContent, /stopped/);

  // Cancelling a delayed permission request must not stop a newer check.
  let resolveOld;
  mediaDevices.getUserMedia = () => new Promise(resolve => { resolveOld = resolve; });
  const pending = run('checkMicrophone()');
  await run('stopMicrophoneCheck()');
  mediaDevices.getUserMedia = async () => stream();
  await run('checkMicrophone()');
  resolveOld(stream()); await pending;
  assert.equal(stoppedTracks, 2);
  assert.equal(run('micCheckActive'), true);
  amplitude = .02; frame();
  assert.ok(get('microphone-level').value > 0);

  run('busy=true; updateMicrophoneCheckControls()');
  assert.equal(get('microphone-level').hidden, false);
  assert.equal(get('check-microphone').disabled, false);
  amplitude=.07;frame();assert.ok(get('microphone-level').value>0);
  await run('checkMicrophone()');
  assert.equal(get('microphone-level').hidden,true);
  await run('checkMicrophone()');
  assert.equal(get('microphone-level').hidden,false);
  amplitude=.03;frame();assert.ok(get('microphone-level').value>0);
  run('busy=false; updateMicrophoneCheckControls()');
  amplitude=0;frame();assert.equal(get('microphone-level').value,0);
  await run('stopMicrophoneCheck()');
  assert.equal(stoppedTracks, 4);
  assert.equal(closedContexts, 3);
  run('busy=false; updateMicrophoneCheckControls()');
  assert.match(get('microphone-check-status').textContent, /stopped/);
  assert.equal(get('check-microphone').disabled, false);
  // During a connected call, inspect its actual sender track without opening
  // another capture or stopping the SDK-owned track when the check is stopped.
  context.MediaStream=class {constructor(tracks){this.tracks=tracks;}getTracks(){return this.tracks;}};
  let callTrackStopped=0;
  const callTrack={kind:'audio',stop(){callTrackStopped++;}};
  context.window.HaqCallAudio={audioTracks:()=>[callTrack]};
  mediaDevices.getUserMedia=async()=>{throw new Error('Must borrow the active call track');};
  run("callState='active'");
  await run('checkMicrophone()');
  assert.equal(run('micCheckOwnsStream'),false);
  amplitude=.04;frame();assert.ok(get('microphone-level').value>0);
  await run('stopMicrophoneCheck()');
  assert.equal(callTrackStopped,0);
  console.log('PASS: level rises/falls before, during and after calls; check starts/stops during calls; cancellation releases only its own audio stream.');
})().catch(error => { console.error(error); process.exitCode = 1; });
