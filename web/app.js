'use strict';
const $ = (id) => document.getElementById(id);
const duration = (n) => Number.isFinite(n) ? `${Math.floor(Math.max(0, n) / 60)}m ${Math.floor(Math.max(0, n) % 60)}s` : 'Unknown';
const node = (tag, text, className) => { const el = document.createElement(tag); el.textContent = text; if (className) el.className = className; return el; };
const list = (id, values, empty = 'None recorded.') => $(id).replaceChildren(...(values.length ? values : [empty]).map(value => node('li', value)));
const terminal = new Set(['complete', 'verified-local', 'blocked', 'budget-exhausted', 'user-stopped']);
const readable = value => String(value ?? '').replaceAll(/[-_]/g, ' ').replace(/^./, c => c.toUpperCase());
const phaseLabels = {discover: 'Understanding your request', plan: 'Planning the work', implement: 'Making changes', verify: 'Checking the results', review: 'Reviewing the work'};
function nextStep(run) {
  const messages = {
    'verified-local': 'The work passed its local checks. You can review the results in your chat. It has not been published.',
    complete: 'The task is complete. Review the results and delivery details in your chat.',
    ready: 'The checks are complete. Publication is still pending; follow the next steps in your chat.',
    blocked: 'Work has stopped because an issue needs resolving. Open your chat to see what is needed.',
    'budget-exhausted': 'Work stopped at the time or attempt limit. Open your chat to review what is finished and decide how to continue.',
    'user-stopped': 'You stopped this task. Open your chat when you are ready to discuss the next step.'
  };
  if (messages[run.status]) return messages[run.status];
  if (run.replan_required) return 'The plan needs updating before work continues. Follow the update in your chat.';
  if ((run.blockers ?? []).some(b => b.status !== 'resolved')) return 'An issue is being investigated. Check the issues below; your chat will explain if input is needed.';
  return 'You do not need to do anything right now. Progress and check results will appear here as work continues.';
}
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
    $('request').textContent = run.request;
    $('mode').textContent = run.mode === 'fix' ? 'Fixing a problem' : 'Building your request';
    const labels = {'ready': 'Verified · publication pending', 'verified-local': 'Verified locally · unpublished', 'complete': 'Complete', 'active': 'In progress', blocked: 'Needs attention', 'budget-exhausted': 'Task limit reached', 'user-stopped': 'Stopped by you'};
    $('state').textContent = labels[run.status] ?? readable(run.status);
    if (run.replan_required) $('state').textContent += ' · Replanning required';
    $('phase').textContent = phaseLabels[run.phase] ?? readable(run.phase);
    $('next-step').textContent = nextStep(run);
    $('budget').textContent = `${duration((terminal.has(run.status) ? run.updated_at : run.now) - run.started_at)} spent${terminal.has(run.status) ? '' : ` · ${duration(run.deadline - run.now)} left`}`;
    const repairLimit = (run.repair_extensions ?? run.events.filter(event => event.kind === 'extend-repairs').map(event => event.detail)).reduce((limit, grant) => grant.limit, run.contract.max_repairs ?? 3);
    $('repairs').textContent = `${run.repairs} of ${repairLimit}`;
    $('check-count').textContent = `${run.contract.checks.filter(c => run.running !== c.id && run.checks[c.id]?.status === 'passed').length} of ${run.contract.checks.length}`;
    $('memory').textContent = 'Notes and decisions are available below';
    list('blockers', (run.blockers ?? []).map(b => `${b.target} — ${readable(b.status)} (${b.attempts} of ${b.limit} attempts)`), 'No issues are currently recorded.');
    list('criteria', run.contract.criteria.map(c => c.text));
    list('scope', run.contract.scope);
    list('non-goals', run.contract.non_goals ?? [], 'No exclusions recorded.');
    $('phases').replaceChildren(...['discover', 'plan', 'implement', 'verify', 'review'].map((phase, i) => {
      const item = node('li', '');
      item.append(node('span', String(i + 1), 'phase-marker'), node('span', phaseLabels[phase]));
      if (phase === run.phase) item.setAttribute('aria-current', 'step');
      return item;
    }));
    $('checks').replaceChildren(...run.contract.checks.map(spec => {
      const result = run.checks[spec.id];
      const state = run.running === spec.id ? 'running' : (result?.status ?? 'not started');
      const item = node('div', '', 'check');
      const detail = node('div', '');
      detail.append(node('strong', spec.title || spec.description || readable(spec.id)), node('small', state === 'running' ? 'This check is running now.' : result ? `${result.test_count == null ? 'Test count not reported' : `${result.test_count} tests reported`} · Took ${duration(result.elapsed_seconds)}` : state === 'running' ? 'This check is running now.' : 'Waiting for this check to start.'));
      item.append(detail, node('span', readable(state), 'check-state ' + (['passed', 'failed'].includes(state) ? state : 'pending')));
      return item;
    }));
    if (!run.contract.checks.length) $('checks').append(node('p', 'No quality checks have been planned yet.', 'empty'));
    const expandedEvents = new Set(Array.from($('events').querySelectorAll('details[open]'), detail => detail.dataset.event));
    $('events').replaceChildren(...(run.events.length ? run.events.slice(-100).reverse().map(e => {
      const item = node('li', '');
      item.append(node('time', new Date(e.at * 1000).toLocaleTimeString()), node('strong', ({init: 'Task started', phase: phaseLabels[e.detail] || 'Moving to the next step', 'check-start': 'Quality check started', 'check-end': 'Quality check finished', repair: 'Working on a fix', review: 'Review recorded', decision: 'Decision recorded', checkpoint: 'Progress saved'})[e.kind] || readable(e.kind)));
      const details = node('details', '');
      details.dataset.event = `${e.at}:${e.kind}`;
      details.open = expandedEvents.has(details.dataset.event);
      details.append(node('summary', 'Technical details'), node('pre', typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail, null, 2)));
      item.append(details);
      return item;
    }) : [node('li', 'No events recorded yet.', 'empty')]));
    const age = run.now - run.updated_at;
    $('activity').textContent = `Last progress update ${duration(age)} ago${age > 180 && !terminal.has(run.status) ? ' — no recent progress has been reported. Check your chat for an update.' : ''}`;
    $('connection').textContent = `Live · updated ${new Date().toLocaleTimeString()}`;
    lastTerminal = terminal.has(run.status);
    $('stop').disabled = lastTerminal || stopping;
    if (lastTerminal) { ended = true; $('connection').textContent = 'Final update · task ended'; }
  } catch (error) {
    $('connection').textContent = `Connection lost — the information shown may be out of date. Reopen the dashboard from your chat.`;
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
