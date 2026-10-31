// Exercise the real review/save functions with a small DOM and mocked HTTP.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function element() {
  return {
    hidden: false, value: '', textContent: '', checked: false, disabled: false,
    children: [], append(...items) { this.children.push(...items); },
    replaceChildren() { this.children = []; }, focus() {},
    querySelector() { return this.label ||= element(); },
  };
}
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, element());
  return nodes.get(id);
};
const context = vm.createContext({
  document: {getElementById: get, createElement: element},
  localStorage: {getItem: () => 'en'},
  window: {addEventListener() {}, dispatchEvent() {}},
  CustomEvent: class {constructor(type,options){this.type=type;this.detail=options.detail;}},
});
const source = fs.readFileSync(path.join(__dirname, '../web/assets/worker-flow.js'), 'utf8');
vm.runInContext(source.replace(/initialize\(\)\.catch\(\(\)=>notify\('page-message',t\('networkError'\)\)\);\s*$/, ''), context);
const run = code => vm.runInContext(code, context);
const response = data => ({ok: true, json: async () => data});
const preview = {
  preview_id: 'revision-1', original_statement: 'Four weeks, first week paid.',
  preferred_name: 'Fictional Worker', workplace_location: 'Hyderabad',
  calculation: {total_earned: '4000.00', payments_received: '1000.00',
    balance: '3000.00', units_worked: 4, pay_basis: 'weekly', rate_per_unit: '1000.00'},
};
let state = {state: 'listening', csrf_token: 'test-csrf', preview};
context.fetch = async () => response(state);

(async () => {
  await run('refreshVoice()');
  assert.equal(get('draft-review').hidden, false);
  assert.match(get('draft-remaining').textContent, /3,000/);
  get('preview-story').value = 'Worker edited this account';
  get('approve-voice').checked = true;
  get('voice-pin').value = '684295';
  await run('refreshVoice()');
  assert.equal(get('preview-story').value, 'Worker edited this account');
  assert.equal(get('voice-pin').value, '684295');
  assert.equal(get('approve-voice').checked, true);

  state = {state: 'needs_clarification', notes: {original_statement: 'Period disputed.'}};
  await run('refreshVoice()');
  assert.equal(get('draft-review').hidden, true);
  assert.equal(get('captured-notes').hidden, false);
  assert.equal(get('voice-pin').value, '');
  assert.equal(get('approve-voice').checked, false);
  assert.equal(get('voice-message').hidden, false);
  state = {state: 'listening', preview};
  await run('refreshVoice()');
  assert.equal(get('draft-review').hidden, false);
  assert.equal(get('preview-editor').hidden, false);

  // Same figures with corrected account text must refresh the review too.
  state = {...state, preview: {...preview, original_statement: 'Corrected account'}};
  await run('refreshVoice()');
  assert.equal(get('preview-story').value, 'Corrected account');

  state = {state: 'awaiting_browser_approval', draft_id: 'tool-draft', draft_kind: 'intake',
    draft: {intake: {preferred_name: 'Worker', original_statement: 'Confirmed'}, calculation: preview.calculation}};
  await run('refreshVoice()');
  assert.equal(get('preview-editor').hidden, true);
  state = {state: 'listening', preview};
  await run('refreshVoice()');
  assert.equal(get('preview-editor').hidden, false);
  assert.equal(run('draft'), null);

  // A state request already in flight must not clear the PIN during saving.
  let releaseState, releaseProposal;
  const requests = [];
  context.fetch = async (url, options) => {
    requests.push(url);
    if (url.startsWith('/voice/intake/state')) {
      return new Promise(resolve => { releaseState = () => resolve(response({state: 'listening'})); });
    }
    if (url === '/voice/intake/prepare-preview') {
      return new Promise(resolve => { releaseProposal = () => resolve(response({draft_id: 'browser-draft'})); });
    }
    assert.equal(url, '/voice/intake/confirm');
    const body = JSON.parse(options.body);
    assert.equal(body.pin, '684295');
    assert.equal(body.draft_id, 'browser-draft');
    assert.equal(body.approved, true);
    return response({case: {case_id: 'HR-FICTIONAL', calculation: preview.calculation}});
  };
  const polling = run('refreshVoice()');
  get('voice-pin').value = '684295';
  get('approve-voice').checked = true;
  const saving = run('approveDraft({preventDefault(){}})');
  const requestCount = requests.length;
  await run('refreshVoice()');
  assert.equal(requests.length, requestCount);
  releaseState();
  await polling;
  assert.equal(get('voice-pin').value, '684295');
  releaseProposal();
  await saving;
  assert.equal(get('voice-saved').hidden, false);
  assert.match(get('voice-saved-reference').textContent, /HR-FICTIONAL/);
  assert.equal(get('voice-pin').value, '');
  assert.equal(get('approve-voice-button').disabled, false);
  console.log('PASS: review updates, edits survive polling, corrections clear approval, and polling cannot interrupt PIN saving.');
})().catch(error => { console.error(error); process.exitCode = 1; });
