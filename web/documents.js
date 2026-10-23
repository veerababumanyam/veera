'use strict';
(() => {
  const get = id => document.getElementById(id);
  let entries = [];
  let selected = new URLSearchParams(location.search).get('doc') || 'task-contract';
  let request = 0;
  let loading = false;
  let lastHTML = null;
  let lastID = null;
  function renderList() {
    const query = get('document-search').value.toLowerCase();
    const children = [];
    let group = '';
    for (const entry of entries.filter(item => item.title.toLowerCase().includes(query))) {
      if (entry.group !== group) {
        group = entry.group;
        const label = document.createElement('p'); label.className = 'doc-group'; label.textContent = group; children.push(label);
      }
      const link = document.createElement('a');
      link.className = 'document-link'; link.textContent = entry.title;
      link.href = '?doc=' + encodeURIComponent(entry.id) + '#documents';
      if (entry.id === selected) link.setAttribute('aria-current', 'page');
      children.push(link);
    }
    if (!children.length) { const empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = 'No matching documents.'; children.push(empty); }
    get('document-list').replaceChildren(...children);
  }
  async function openDocument(id, focus = false, quiet = false) {
    const current = ++request;
    loading = true;
    selected = id;
    if (!quiet) { renderList(); get('document-status').textContent = 'Loading document…'; }
    try {
      const response = await fetch('document/' + encodeURIComponent(id), {cache: 'no-store', signal: AbortSignal.timeout(4000)});
      if (!response.ok) throw new Error(response.status === 410 ? 'Task replaced. Open its current dashboard.' : 'Document unavailable. Select another document or try again.');
      const data = await response.json();
      if (current !== request) return;
      get('document-title').textContent = data.title;
      get('document-source').textContent = data.source;
      // Server emits only escaped text and an allowlisted HTML subset, never file HTML.
      if (data.html !== lastHTML || id !== lastID) {
        if (id !== lastID) get('document-content').closest('article').scrollTop = 0;
        get('document-content').innerHTML = data.html;
        lastHTML = data.html; lastID = id;
      }
      get('document-status').textContent = '';
      if (focus) get('document-title').focus({preventScroll: true});
    } catch (error) {
      if (current !== request) return;
      get('document-status').textContent = error.message;
      if (!quiet) { get('document-content').replaceChildren(); lastHTML = null; lastID = null; }
    } finally { if (current === request) loading = false; }
  }
  document.addEventListener('click', event => {
    const anchor = event.target.closest('a');
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (!anchor.getAttribute('href')?.startsWith('?doc=')) return;
    const target = new URL(anchor.href, location.href);
    if (target.origin !== location.origin || target.pathname !== location.pathname || !target.searchParams.has('doc')) return;
    event.preventDefault();
    history.pushState(null, '', target.href);
    get('documents').scrollIntoView();
    openDocument(target.searchParams.get('doc'), true);
  });
  window.addEventListener('popstate', () => openDocument(new URLSearchParams(location.search).get('doc') || 'task-contract'));
  get('document-search').addEventListener('input', renderList);
  async function initialize() {
    try {
      const response = await fetch('documents', {cache: 'no-store', signal: AbortSignal.timeout(4000)});
      if (!response.ok) throw new Error('Document library unavailable. Reload to retry.');
      entries = await response.json();
      renderList();
      await openDocument(selected);
    } catch (error) { get('document-status').textContent = error.message; get('document-list').textContent = 'Could not load the library.'; }
  }
  initialize();
  setInterval(() => { if (!loading && selected.startsWith('task-')) openDocument(selected, false, true); }, 4000);
})();
