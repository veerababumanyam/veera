'use strict';
const $ = (id) => document.getElementById(id);
const duration = (n) => `${Math.floor(Math.max(0, n) / 60)}m ${Math.floor(Math.max(0, n) % 60)}s`;
const list = (id, values) => $(id).replaceChildren(...values.map((value) => {
  const li = document.createElement('li'); li.textContent = value; return li;
}));
let busy = false;
async function refresh() {
  if (busy) return;
  busy = true;
  try {
    const response = await fetch('status', {cache: 'no-store', signal: AbortSignal.timeout(4000)});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const run = await response.json();
    $('request').textContent = `${run.mode.toUpperCase()}: ${run.request}`;
    $('state').textContent = run.status === 'ready' ? 'Verified · publication pending' : run.status;
    if (run.replan_required) $('state').textContent += ' · PM replanning required';
    $('phase').textContent = run.phase;
    $('budget').textContent = `${duration(run.now - run.started_at)} / ${duration(run.deadline - run.now)}`;
    $('repairs').textContent = `${run.repairs} / ${run.contract.max_repairs ?? 3}`;
    $('memory').textContent = `Shared memory revision ${run.memory_revision ?? 0}`;
    list('blockers', (run.blockers ?? []).map(b => `${b.id}: ${b.target} · ${b.status} · ${b.attempts}/${b.limit} attempts`));
    list('criteria', run.contract.criteria.map(c => `${c.id}: ${c.text}`));
    list('scope', run.contract.scope);
    list('non-goals', run.contract.non_goals ?? []);
    $('checks').replaceChildren(...run.contract.checks.map(spec => {
      const result = run.checks[spec.id];
      const item = document.createElement('div');
      const state = result?.status ?? (run.running === spec.id ? 'running' : 'not run');
      item.className = `check ${state}`;
      item.textContent = `${spec.id}: ${state}${result ? ` · exit ${result.exit_code ?? 'unknown'} · tests ${result.test_count ?? 'N/A'} · ${duration(result.elapsed_seconds)}` : ''}`;
      return item;
    }));
    list('events', run.events.slice(-100).reverse().map(e => `${new Date(e.at * 1000).toLocaleTimeString()} · ${e.kind}: ${typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail)}`));
    const age = run.now - run.updated_at;
    $('activity').textContent = `Last meaningful event ${duration(age)} ago${age > 180 ? ' — inspect for a stalled worker' : ''}`;
    $('connection').textContent = `Live · updated ${new Date().toLocaleTimeString()}`;
    $('stop').disabled = ['complete', 'blocked', 'budget-exhausted', 'user-stopped'].includes(run.status);
  } catch (error) {
    $('connection').textContent = `Disconnected — displayed state may be stale (${error.message})`;
    $('stop').disabled = true;
  } finally { busy = false; }
}
$('stop').addEventListener('click', async () => {
  $('stop').disabled = true;
  try {
    const response = await fetch('stop', {method: 'POST', headers: {'X-Delivery-Control': 'stop'}, signal: AbortSignal.timeout(4000)});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await refresh();
  } catch (error) { $('connection').textContent = `Stop not confirmed: ${error.message}`; }
});
refresh();
setInterval(refresh, 2000);
