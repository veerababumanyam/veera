'use strict';
// Execute the real dashboard JS against a minimal DOM, no npm dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const elements = new Map();
function element() { return {textContent: '', disabled: false, children: [], replaceChildren(...items) {this.children = items;}, addEventListener(type, callback) {this[type] = callback;}}; }
const get = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
let fail = false;
const requests = [];
const run = {mode: 'fix', request: '<img onerror=alert(1)>', status: 'active', phase: 'verify', now: 200, started_at: 100, updated_at: 199, deadline: 300, repairs: 1, contract: {criteria: [{id: 'C1', text: 'Done'}], scope: ['app.py'], checks: [{id: 'unit'}], non_goals: []}, checks: {}, events: []};
const context = vm.createContext({document: {getElementById: get, createElement: element}, AbortSignal, Date, setInterval() {}, fetch: async (url, options) => {requests.push([url, options]); if (fail) throw new Error('offline'); return {ok: true, json: async () => run}; }});
(async () => {
  vm.runInContext(source, context);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(get('request').textContent, 'FIX: <img onerror=alert(1)>');
  assert.equal(get('checks').children[0].textContent, 'unit: not run');
  assert.match(get('connection').textContent, /Live/);
  await get('stop').click();
  assert(requests.some(([url, options]) => url === 'stop' && options.method === 'POST' && options.headers['X-Delivery-Control'] === 'stop'));
  fail = true;
  await vm.runInContext('refresh()', context);
  assert.match(get('connection').textContent, /Disconnected/);
  assert.equal(get('stop').disabled, true);
  console.log('PASS: 6 dashboard JS assertions (rendering, not-run, connection, stop, disconnect, disabled control)');
})().catch(error => {console.error(error); process.exitCode = 1;});
