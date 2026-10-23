'use strict';
const $ = (id) => document.getElementById(id);
const duration = (n) => Number.isFinite(n) ? `${Math.floor(Math.max(0, n) / 60)}m ${Math.floor(Math.max(0, n) % 60)}s` : 'Unknown';
const node = (tag, text, className) => { const el = document.createElement(tag); el.textContent = text; if (className) el.className = className; return el; };
const list = (id, values, empty = 'None recorded.') => $(id).replaceChildren(...(values.length ? values : [empty]).map(value => node('li', value)));
const terminal = new Set(['complete', 'verified-local', 'blocked', 'budget-exhausted', 'user-stopped']);
let busy = false;
let stopping = false;
let lastTerminal = true;
let ended = false;
async function refresh() {
  if (busy || ended) return;
  busy = true;
  try {
    const response = await fetch('status', {cache: 'no-store', signal: AbortSignal.timeout(4000)});
    if (response.status === 410) { ended = true; throw new Error('This task has been replaced. Open its current dashboard.'); }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const run = await response.json();
    $('request').textContent = `${run.mode.toUpperCase()}: ${run.request}`;
    $('mode').textContent = run.mode.toUpperCase();
    const labels = {'ready': 'Verified · publication pending', 'verified-local': 'Verified locally · unpublished', 'complete': 'Complete · published', 'active': 'In progress'};
    $('state').textContent = labels[run.status] ?? run.status;
    if (run.replan_required) $('state').textContent += ' · Replanning required';
    $('phase').textContent = run.phase;
    $('budget').textContent = `${duration(run.now - run.started_at)} / ${duration(run.deadline - run.now)}`;
    $('repairs').textContent = `${run.repairs} / ${run.contract.max_repairs ?? 3}`;
    $('check-count').textContent = `${run.contract.checks.filter(c => run.checks[c.id]?.status === 'passed').length} / ${run.contract.checks.length}`;
    $('memory').textContent = `Shared memory revision ${run.memory_revision ?? 0}`;
    list('blockers', (run.blockers ?? []).map(b => `${b.id}: ${b.target} · ${b.status} · ${b.attempts}/${b.limit} attempts`), 'No blockers recorded.');
    list('criteria', run.contract.criteria.map(c => `${c.id}: ${c.text}`));
    list('scope', run.contract.scope);
    list('non-goals', run.contract.non_goals ?? [], 'No exclusions recorded.');
    $('phases').replaceChildren(...['discover', 'plan', 'implement', 'verify', 'review'].map((phase, i) => {
      const item = node('li', '');
      item.append(node('span', String(i + 1), 'phase-marker'), node('span', phase));
      if (phase === run.phase) item.setAttribute('aria-current', 'step');
      return item;
    }));
    $('checks').replaceChildren(...run.contract.checks.map(spec => {
      const result = run.checks[spec.id];
      const state = result?.status ?? (run.running === spec.id ? 'running' : 'not run');
      const item = node('div', '', 'check');
      const detail = node('div', '');
      detail.append(node('strong', spec.id), node('small', result ? `Exit ${result.exit_code ?? 'unknown'} · Tests ${result.test_count ?? 'N/A'} · ${duration(result.elapsed_seconds)}` : (spec.kind ?? 'Verification') + ' · Awaiting evidence'));
      item.append(detail, node('span', state, 'check-state ' + (['passed', 'failed'].includes(state) ? state : 'pending')));
      return item;
    }));
    $('events').replaceChildren(...(run.events.length ? run.events.slice(-100).reverse().map(e => {
      const item = node('li', '');
      item.append(node('time', new Date(e.at * 1000).toLocaleTimeString()), node('strong', e.kind.replaceAll('-', ' ')), node('p', typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail, null, 2)));
      return item;
    }) : [node('li', 'No events recorded yet.', 'empty')]));
    const age = run.now - run.updated_at;
    $('activity').textContent = `Last meaningful event ${duration(age)} ago${age > 180 && !terminal.has(run.status) ? ' — inspect for a stalled worker' : ''}`;
    $('connection').textContent = `Live · updated ${new Date().toLocaleTimeString()}`;
    lastTerminal = terminal.has(run.status);
    $('stop').disabled = lastTerminal || stopping;
  } catch (error) {
    $('connection').textContent = `Disconnected — displayed state may be stale (${error.message})`;
    $('stop').disabled = true;
  } finally { busy = false; }
}
$('stop').addEventListener('click', async () => {
  if (stopping || lastTerminal) return;
  stopping = true;
  $('stop').disabled = true;
  try {
    const response = await fetch('stop', {method: 'POST', headers: {'X-Delivery-Control': 'stop'}, signal: AbortSignal.timeout(4000)});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    lastTerminal = true;
    await refresh();
  } catch (error) { $('connection').textContent = `Stop not confirmed: ${error.message}`; }
  finally { stopping = false; }
});
refresh();
setInterval(refresh, 2000);
