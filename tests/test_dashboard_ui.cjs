const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
class Element {
  constructor() { this.children = []; this.textContent = ''; this.attributes = {}; this.dataset = {}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener() {}
  querySelectorAll() { return []; }
}
async function render(overrides = {}, fail = false) {
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const run = {mode: 'build', request: '<img src=x onerror=alert(1)>', status: 'active', phase: 'implement', now: 200, started_at: 100, updated_at: 190, deadline: 500, repairs: 0, contract: {criteria: [{id:'C1', text:'Easy to read'}], checks: [{id:'browser-check'}], scope: []}, checks: {}, events: [{at: 190, kind:'init', detail:{privateLabel:'raw data'}}], ...overrides};
  const context = {document: {getElementById: get, createElement: () => new Element()}, fetch: async () => {if(fail) throw new Error('offline'); return {ok:true, json:async()=>run};}, AbortSignal, setInterval:()=>{}};
  vm.runInNewContext(source, context);
  await new Promise(resolve=>setImmediate(resolve));
  return {get, context};
}
(async()=>{
  let view = await render();
  assert.equal(view.get('phase').textContent, 'Making changes');
  assert.match(view.get('next-step').textContent, /do not need to do anything/);
  assert.equal(view.get('request').textContent, '<img src=x onerror=alert(1)>');
  assert.equal(view.get('checks').children[0].children[1].textContent, 'Not started');
  assert.equal(view.get('events').children[0].children[2].children[0].textContent, 'Technical details');
  for (const [status, message] of [['blocked', /issue needs resolving/], ['verified-local', /not been published/], ['complete', /task is complete/], ['budget-exhausted', /limit/], ['user-stopped', /You stopped/], ['ready', /Publication is still pending/]]) {
    view = await render({status});
    assert.match(view.get('next-step').textContent, message);
    assert.equal(view.get('stop').disabled, status !== 'ready');
  }
  view = await render({running:'browser-check', checks:{'browser-check':{status:'passed', test_count:2}}});
  assert.equal(view.get('checks').children[0].children[1].textContent, 'Running');
  assert.equal(view.get('check-count').textContent, '0 of 1');
  assert.match(view.get('checks').children[0].children[0].children[1].textContent, /running now/);
  view = await render({repairs:3, events:[{at:190, kind:'extend-repairs', detail:{limit:23}}]});
  assert.equal(view.get('repairs').textContent, '3 of 23');
  view = await render({}, true);
  assert.match(view.get('connection').textContent, /out of date/);
  assert.equal(view.get('stop').disabled, true);
  console.log('Dashboard state rendering checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
