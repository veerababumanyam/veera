"""Bounded HTML views of task records and packaged documentation, never arbitrary files."""
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 256 * 1024
TASK_DOCS = {'task-contract': 'What success looks like', 'task-discovery': 'Requirements & plan', 'task-intake': 'Intake & approvals', 'task-review': 'Independent review',
             'task-decisions': 'Decisions', 'task-memory': 'Task notes', 'task-checkpoint': 'Checkpoint'}


def package_docs():
    return {'guide-overview': ROOT / 'README.md', 'guide-codex': ROOT / 'adapters/codex/README.md',
            **{'guide-docs-' + path.stem: path for path in sorted((ROOT / 'docs').glob('*.md'))}}


def catalog():
    return ([{'id': key, 'title': title, 'group': 'This task'} for key, title in TASK_DOCS.items()]
            + [{'id': key, 'title': ('Veera overview' if path == ROOT / 'README.md' else
                                    'Codex compatibility' if path == ROOT / 'adapters/codex/README.md' else
                                    path.stem.replace('-', ' ').capitalize()), 'group': 'Veera handbook'}
               for key, path in package_docs().items()])


def inline(text, origin=None):
    """Only local catalog links are clickable; HTML and all other URLs stay text."""
    parts = []
    last = 0
    for match in re.finditer(r'\[([^\]\n]+)\]\(([^)\n]+)\)', text):
        parts.append(rich_text(text[last:match.start()]))
        label, target = match.groups()
        destination = None
        if origin is not None and not re.match(r'^[a-zA-Z][\w+.-]*:', target):
            resolved = (origin.parent / target.split('#', 1)[0]).resolve()
            destination = next((key for key, path in package_docs().items() if path.resolve() == resolved), None)
        parts.append(f'<a href="?doc={destination}#documents">{escape(label)}</a>' if destination else escape(match.group(0)))
        last = match.end()
    parts.append(rich_text(text[last:]))
    return ''.join(parts)


def rich_text(text):
    text = escape(text)
    return re.sub(r'`([^`\n]+)`|\*\*([^*\n]+)\*\*', lambda match:
                  '<code>' + match[1] + '</code>' if match[1] is not None else '<strong>' + match[2] + '</strong>', text)


def markdown(text, origin=None):
    """A small escaped Markdown subset; no raw HTML, embedded media or scripts."""
    output, paragraph, code = [], [], []
    in_code = False
    list_kind = None

    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph), origin) + '</p>')
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            output.append('</' + list_kind + '>')
            list_kind = None

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith('```'):
            flush()
            close_list()
            if in_code:
                output.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>')
                code.clear()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        if not line.strip():
            flush()
            close_list()
            continue
        heading = re.match(r'^(#{1,6})\s+(.+)$', line)
        item = re.match(r'^\s*(?:([-*])|\d+[.])\s+(.+)$', line)
        if heading:
            flush()
            close_list()
            level = min(len(heading[1]) + 1, 6)
            output.append(f'<h{level}>' + inline(heading[2], origin) + f'</h{level}>')
        elif line.startswith('|') and i < len(lines) and re.fullmatch(r'[| :\-]+', lines[i]):
            flush()
            close_list()
            headers = line.strip('|').split('|')
            output.append('<div class="table-scroll"><table><thead><tr>' + ''.join('<th>' + inline(h.strip(), origin) + '</th>' for h in headers) + '</tr></thead><tbody>')
            i += 1
            while i < len(lines) and lines[i].startswith('|'):
                output.append('<tr>' + ''.join('<td>' + inline(c.strip(), origin) + '</td>' for c in lines[i].strip('|').split('|')) + '</tr>')
                i += 1
            output.append('</tbody></table></div>')
        elif item:
            flush()
            kind = 'ul' if item[1] else 'ol'
            if list_kind != kind:
                close_list()
                output.append('<' + kind + '>')
                list_kind = kind
            output.append('<li>' + inline(item[2], origin) + '</li>')
        else:
            close_list()
            paragraph.append(line)
    flush()
    close_list()
    if in_code:
        output.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>')
    return '\n'.join(output)


def record_html(value):
    if value is None:
        return '<span class="muted">Not recorded</span>'
    if isinstance(value, dict):
        return '<dl class="record">' + ''.join('<div><dt>' + escape(str(key).replace('_', ' ').capitalize()) + '</dt><dd>' + record_html(item) + '</dd></div>' for key, item in value.items()) + '</dl>'
    if isinstance(value, list):
        return '<ul class="record-list">' + ''.join('<li>' + record_html(item) + '</li>' for item in value) + '</ul>' if value else '<span class="muted">None recorded</span>'
    return '<span>' + escape(str(value)) + '</span>'


def document(identifier, state):
    if identifier in TASK_DOCS:
        values = {'task-contract': state['contract'], 'task-discovery': state['contract'].get('discovery'), 'task-intake': state['contract'].get('intake'), 'task-review': state.get('review'),
                  'task-checkpoint': state.get('checkpoint'),
                  'task-decisions': [e for e in state.get('events', []) if e['kind'] in ('decision', 'replan')],
                  'task-memory': list(state.get('context', {}).get('items', {}).values())}
        value = values[identifier]
        if len(json.dumps(value).encode()) > MAX_BYTES:
            raise ValueError('Task document exceeds display limit')
        title = TASK_DOCS[identifier]
        if not value:
            html = '<p class="empty">No ' + escape(title.lower()) + ' recorded yet.</p>'
        elif identifier == 'task-contract':
            html = '<h3>Acceptance criteria</h3><ul>' + ''.join('<li><strong>' + escape(c['id']) + '</strong> · ' + escape(c['text']) + '</li>' for c in value['criteria']) + '</ul><h3>Authorized scope</h3><ul>' + ''.join('<li>' + escape(p) + '</li>' for p in value['scope']) + '</ul>'
            html += '<h3>Frozen specification</h3>' + record_html({key: item for key, item in value.items() if key not in ('criteria', 'scope')})
        else:
            html = record_html(value)
        return {'id': identifier, 'title': title, 'html': html, 'source': 'Current task record'}
    paths = package_docs()
    if identifier not in paths:
        raise KeyError(identifier)
    path = paths[identifier]
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (path, *path.parents)) or not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Unsafe document path')
    with path.open('rb') as stream:
        content = stream.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError('Document exceeds display limit')
    title = next(entry['title'] for entry in catalog() if entry['id'] == identifier)
    return {'id': identifier, 'title': title, 'html': markdown(content.decode('utf-8'), path),
            'source': path.relative_to(ROOT).as_posix()}
