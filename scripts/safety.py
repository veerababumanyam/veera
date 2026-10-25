#!/usr/bin/env python3
"""Defense-in-depth hook, not an OS sandbox or a shell authorization parser."""
import json
import os
from pathlib import Path
import re
import shlex
import sys
import ownership
STATE = '.veera'
TERMINAL = {'complete', 'verified-local', 'blocked', 'budget-exhausted', 'user-stopped'}


def shell_words(command):
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    if os.name == 'nt':
        lexer.escape = ''  # PowerShell/Windows paths use literal backslashes.
    words = list(lexer)
    # Canonicalize only the known controller path; preserve every other token.
    controller = Path(__file__).resolve().parent / 'delivery.py'
    script_index = 2 if os.name == 'nt' and words[:1] == ['&'] else 1
    if len(words) > script_index and shell_path(words[script_index], Path.cwd()) == controller:
        words[script_index] = str(controller)
    # PowerShell uses & to invoke a quoted executable. Recognize it only for
    # the exact controller, never as a general shell-chain exception.
    if script_index == 2 and controller_command(words[1:]):
        words = words[1:]
    return words


def status(root):
    from delivery import status as implementation
    return implementation(root)


def controller_command(words):
    # Bare interpreter names come from PATH, never from the session's folder.
    # Git Bash spells the host's own interpreter /c/Users/...; it is the same file.
    return (len(words) >= 3 and words[1] == str(Path(__file__).resolve().parent / 'delivery.py')
            and (words[0] in ('python3', 'python', 'py') or shell_path(words[0], Path.cwd()) == Path(sys.executable).resolve()))


HOST_ENV = re.compile(r'(?:(?:env|export)\s+)?(\$env:)?(CLAUDE_PLUGIN_DATA|VEERA_HOST)\s*=\s*("[^"$`]*"|\'[^\']*\'|[^\s;&|$`"\']+)\s*(?:;|&&)?\s*')
ANCHOR = re.compile(r'(?:cd|Set-Location|pushd)\s+(?:-(?:Literal)?Path\s+)?("[^"]+"|\'[^\']+\'|[^\s;&|]+)\s*(?:&&|;)\s*', re.I)
# A trailing `2>&1` and output filters that name no path, e.g. `| tail -20`.
OUTPUT_TAIL = re.compile(r'(?:\s+2>&1)?(?:\s*\|\s*(?:head|tail|grep|findstr|wc|Select-Object|Select-String|Out-String)'
                         r'(?:\s+(?:[^\s|;&<>"\'`$/\\~]+|"[^"|;&<>`$/\\~]*"|\'[^\'|;&<>/\\~]*\'))*)*\s*$', re.I)


# Windows paths keep their backslashes in double quotes; escapes that change text do not.
LOCAL_VARIABLE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("(?:[^"$`\\]|\\(?![\\"$`]))*"|\'[^\'$`]*\'|[^\s;&|$`"\'<>()\\]*)')
# Shell or process settings a plain assignment could change for the controller.
SHELL_SETTINGS = re.compile(r'(?:PATH|PATHEXT|IFS|ENV|BASH_ENV|HOME|SHELLOPTS|BASHOPTS|PS4|COMSPEC|TEMP|TMP|PYTHON.*|LD_.*|DYLD_.*|GIT_.*|CLAUDE.*|VEERA.*)', re.I)


def unquoted(text):
    """The text with complete quoted strings blanked; an open quote stays visible."""
    return re.sub(r'"[^"]*"|\'[^\']*\'', '""', text)


def statements(text):
    """Split at `&&` and `;` outside quotes; None for `||`, a background `&` or open quotes."""
    parts, current, quote, index = [], '', None, 0
    while index < len(text):
        c = text[index]
        if quote:
            quote = None if c == quote else quote
        elif c in '"\'':
            quote = c
        elif text.startswith('&&', index) or c == ';':
            parts.append(current.strip())
            current, index = '', index + (2 if c == '&' else 1)
            continue
        elif text.startswith('||', index):
            return None
        elif c == '&' and not current.endswith('>') and current.strip():
            return None  # `2>&1` and PowerShell's leading call operator are not jobs.
        current += c
        index += 1
    parts.append(current.strip())
    return None if quote or not all(parts) else parts


def controller_form(command, root):
    """Unwrap one controller call from the forms hosts document for children.

    Statements before the call may anchor into the owned worktree, run confined
    task commands there, set host identity as `NAME=value`, `env`/`export
    NAME=value` or PowerShell `$env:NAME = 'value'` for CLAUDE_PLUGIN_DATA and
    VEERA_HOST only, or name a local shell variable (`T="..."`) that later
    statements use as `$T`. Identity values must equal this hook's own host
    environment, so the wrapper adds no authority. Returns (bare controller
    command or None, refusal or None, anchored, ran other commands first).
    """
    text = command.strip()
    if '\n' in text or '`' in text or '$(' in text:
        return None, None, False, False
    parts = statements(text)
    if parts is None:
        return None, None, False, False
    values, variables, base, prefixed, call = {}, {}, None, False, None
    for index, part in enumerate(parts):
        for name, value in variables.items():
            if re.search(r"'[^']*\$", part):
                return None, None, False, False  # Single quotes never expand.
            part = re.sub(r'\$(?:\{' + name + r'\}|' + name + r'(?![A-Za-z0-9_]))', lambda _: value, part)
        anchor = ANCHOR.match(part + ' ;')
        if anchor and anchor.end() >= len(part):
            target = anchor.group(1).strip('"\'')
            folder = shell_path(target, base) if base and not absolute(target) else None
            if folder is not None and inside(folder, root):
                base = folder
            elif absolute_inside(target, root):
                base = shell_path(target, root)
            else:
                return None, None, False, False
            continue
        while (match := HOST_ENV.match(part)):
            value = match.group(3).strip('"\'')
            if values.setdefault(match.group(2), value) != value:
                return None, 'Duplicate host identity values are not allowed.', False, False
            part = part[match.end():]
        if not part:
            continue
        local = LOCAL_VARIABLE.fullmatch(part)
        if local and index < len(parts) - 1:
            if SHELL_SETTINGS.fullmatch(local.group(1)) or local.group(1) in os.environ:
                return None, None, False, False
            variables[local.group(1)] = local.group(2).strip('"\'')
            continue
        if index < len(parts) - 1:
            # A confined task command before the call, e.g. `git diff --stat`.
            parsed = chain(part)
            if base is None or parsed is None or parsed[1] or task_command(parsed[0][0], base, root) is None:
                return None, None, False, False
            base, prefixed = task_command(parsed[0][0], base, root), True
            continue
        call = part
    if call is None:
        return None, None, False, False  # The controller call comes last.
    text = call
    if text.startswith(('env ', 'export ')):
        return None, None, False, False  # Any other variable is not a documented controller form.
    text = OUTPUT_TAIL.sub('', text, count=1)  # Trimming the report adds no authority.
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    if os.name == 'nt':
        lexer.escape = ''
    try:
        if any(t in (';', '&&', '||', '|', '&', '>', '>>', '<') for t in lexer) or '$' in text:
            return None, None, False, False
        if not controller_command(shell_words(text)):
            return None, None, False, False
    except ValueError:
        return None, None, False, False
    data = os.environ.get('CLAUDE_PLUGIN_DATA')
    host = os.environ.get('VEERA_HOST') or 'claude'
    if 'CLAUDE_PLUGIN_DATA' in values and not (data and Path(values['CLAUDE_PLUGIN_DATA']).resolve() == Path(data).resolve()):
        return None, 'Controller identity does not match the calling host session.', False, False
    if values.get('VEERA_HOST', host) != host:
        return None, 'Controller identity does not match the calling host session.', False, False
    return text, None, base is not None, prefixed


def relative_inputs(words):
    """Controller file options a shell in the original checkout would read there."""
    for index, word in enumerate(words):
        flag, _, value = word.partition('=')
        if flag in ('--contract', '--file'):
            value = value or (words[index + 1] if index + 1 < len(words) else '')
            if value and not absolute(value):
                yield flag, value


def scoped(name, scope):
    from delivery import scoped as implementation
    return implementation(name, scope)

READ_ONLY = {'Read', 'Glob', 'Grep', 'ToolSearch', 'ListAgents'}
CODEX_CHAT_RECOVERY = {'mcp__codex_app__list_threads', 'mcp__codex_app__list_projects',
                       'mcp__codex_app__read_thread', 'mcp__codex_app__wait_threads',
                       'mcp__codex_app__send_message_to_thread'}
DANGEROUS = re.compile(r'(?:\bgit\s+(?:push|reset\s+--hard|clean\s+-)|\brm\s+[^\n]*-[a-zA-Z]*[rf]|\bsudo\b|\bcurl\b.*\|\s*(?:ba)?sh|\b(?:npm|pnpm)\s+publish\b|\bkubectl\b|\bterraform\s+(?:apply|destroy)\b|\bchmod\s+777\b|\bDROP\s+(?:TABLE|DATABASE)\b)', re.I)
# Anchored task commands: one simple command after an explicit change into the
# owned worktree. Local Git only; nested shells and inline code stay reviewable.
GIT_LOCAL = {'status', 'diff', 'log', 'show', 'add', 'commit', 'grep', 'ls-files', 'rev-parse', 'blame', 'apply', 'restore'}
NESTED_SHELLS = {'sh', 'bash', 'zsh', 'cmd', 'pwsh', 'powershell', 'invoke-expression', 'iex', 'start-process', 'xargs', 'eval', 'exec', 'env', 'sudo', 'nohup', 'cd', 'set-location', 'pushd'}
INTERPRETERS = {'python', 'python3', 'py', 'node', 'perl', 'ruby'}
FILTERS = {'head', 'tail', 'grep', 'sort', 'wc', 'select-object', 'select-string', 'findstr', 'out-string'}


def inside(path, root):
    """True for a path in the owned tree that is not inside a nested repository."""
    if not path.is_relative_to(root):
        return False
    for parent in [path if path.is_dir() else path.parent, *path.parents]:
        if parent == root:
            return True
        if (parent / '.git').exists():
            return False
    return True


def original_checkout(root):
    """The checkout this owner's workspace was created from, as recorded by `workspace`.

    Read only after ownership.authorize validated the owned metadata identity.
    """
    try:
        value = json.loads((root / STATE / 'workspace.json').read_text())
        original = Path(value['original']).resolve()
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if original == root or original.is_relative_to(root) or root.is_relative_to(original):
        return None
    return original


def shell_path(word, base):
    if os.name == 'nt' and re.fullmatch(r'/[A-Za-z](?:/.*)?', word):
        word = word[1] + ':/' + word[3:]  # Git Bash drive form /c/... on Windows.
    return (base / Path(word).expanduser()).resolve()


def absolute(word):
    return Path(word).is_absolute() or bool(os.name == 'nt' and re.fullmatch(r'/[A-Za-z](?:/.*)?', word))


def absolute_inside(word, root):
    """An anchor target must be absolute: a relative one resolves from the shell's
    real folder, which for a desktop session is the original checkout."""
    return absolute(word) and inside(shell_path(word, root), root)


def host_tool_output(path, session_id):
    """Claude Code saves long tool output for this session under its config folder."""
    config = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude').resolve()
    parts = path.parts
    return (path.is_relative_to(config / 'projects') and 'tool-results' in parts
            and parts[parts.index('tool-results') - 1] == session_id)


def task_command(words, base, root):
    """Validate one simple command of an anchored chain; returns its folder or None."""
    name = lambda word: Path(word).name.lower().removesuffix('.exe')
    while words and re.match(r'[A-Za-z_][A-Za-z0-9_]*=', words[0]):
        words = words[1:]  # Leading variables; their values are path-checked below.
    if not words:
        return None
    program = name(words[0])
    if program in ('cd', 'set-location', 'pushd'):
        target = [w for w in words[1:] if w.lower() not in ('-path', '-literalpath')]
        if len(target) != 1:
            return None
        folder = shell_path(target[0], base)
        return folder if inside(folder, root) else None
    checked = words
    if program == 'git':
        # A commit author given inline; any other -c setting can run programs.
        while len(words) > 3 and words[1] == '-c' and re.match(r'user\.(?:name|email)=', words[2]):
            words = [words[0], *words[3:]]
        if len(words) > 3 and words[1] == '-C':
            if not inside(shell_path(words[2], base), root):
                return None
            words = [words[0], *words[3:]]
        if len(words) < 2 or words[1] not in GIT_LOCAL:
            return None
    elif program in ('docker', 'podman'):
        # Container-side arguments are interpreted inside the container.
        return base if len(words) > 2 and words[1] == 'exec' else None
    elif program in ('bash', 'sh'):
        if len(words) < 2 or any(w.startswith('-') for w in words[1:]):
            return None  # A script file is checked like any other; -c strings are not.
    elif program in NESTED_SHELLS:
        return None
    if program in INTERPRETERS and any(w in ('-c', '-e', '--eval') for w in words):
        return None
    for word in checked:
        for value in (word, word.split('=', 1)[1] if '=' in word else ''):
            pathlike = (value.startswith(('/', '\\', '~')) or re.match(r'[A-Za-z]:[\\/]', value)
                        or '..' in re.split(r'[\\/]', value))
            if pathlike and not inside(shell_path(value, base), root):
                return None
    return base


def anchored(command, root):
    """Accept `cd <worktree> && cmd [&& cmd] [| filter]` or `git -C <worktree> cmd`.

    Defense in depth, not a shell sandbox: every path-like argument must stay in
    the owned worktree, and anything the grammar does not recognize is refused.
    Controller calls are recognized separately by controller_form.
    """
    parsed = chain(command)
    if parsed is None:
        return False
    segments, operators = parsed
    first = segments[0]
    program = Path(first[0]).name.lower().removesuffix('.exe')
    if program in ('cd', 'set-location', 'pushd'):
        target = [w for w in first[1:] if w.lower() not in ('-path', '-literalpath')]
        if len(target) != 1 or not operators or operators[0] == '|' or not absolute_inside(target[0], root):
            return False
    elif not (program == 'git' and len(first) > 3 and first[1] == '-C' and absolute_inside(first[2], root)):
        return False
    base = root
    for index, segment in enumerate(segments):
        if index and operators[index - 1] == '|':
            if Path(segment[0]).name.lower().removesuffix('.exe') not in FILTERS or task_command(segment, base, root) is None:
                return False
            continue
        base = task_command(segment, base, root)
        if base is None:
            return False
    return True


def chain(command):
    """Split a one-line command into simple commands joined by && || ; or |.

    Returns (segments, operators), or None for substitution, redirection to a
    file, background jobs, owner options or a known destructive action.
    """
    if '\n' in unquoted(command) or '`' in command or '$' in command:
        return None  # A quoted newline, as in a commit message body, is text.
    if '--session-id' in command or '--capability-file' in command or DANGEROUS.search(command):
        return None
    command = re.sub(r'\s+\d?>\s*(?:&1|/dev/null|NUL)(?=\s|$)', '', command)
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    if os.name == 'nt':
        lexer.escape = ''
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    segments, operators, current = [], [], []
    for token in tokens:
        if token and all(c in '();<>|&' for c in token):
            operators.append(token)
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    if not all(segments) or any(op not in ('&&', '||', ';', '|') for op in operators):
        return None
    return segments, operators


# Commands a shell left in the original checkout may run there: reads and
# listings only, plus container execution, whose arguments the host never sees.
READ_ONLY = {'pwd', 'ls', 'dir', 'cat', 'type', 'head', 'tail', 'wc', 'grep', 'rg', 'findstr', 'find', 'sed', 'sort', 'git',
             'stat', 'file', 'get-location', 'get-childitem', 'get-content', 'select-string', 'select-object', 'test-path',
             'resolve-path', 'out-string'}
GIT_READ = {'status', 'diff', 'log', 'show', 'grep', 'ls-files', 'rev-parse', 'blame'}
WRITING_OPTIONS = {'find': ('-exec', '-execdir', '-ok', '-okdir', '-delete', '-fprint', '-fprint0', '-fprintf', '-fls'),
                   'rg': ('--pre',), 'sort': ('-o', '--output'),
                   'git': ('-O', '--open-files-in-pager', '--output', '--ext-diff', '--textconv')}


def origin_command(command, cwd, original, root):
    """Accept read-only inspection from the original checkout, and containers.

    Every path-like argument must resolve in the original checkout or the owned
    worktree; nested repositories, other projects and any write stay refused.
    """
    parsed = chain(command)
    if parsed is None:
        return False
    segments, operators = parsed
    base = cwd
    readable = lambda path: inside(path, original) or inside(path, root)
    for index, words in enumerate(segments):
        program = Path(words[0]).name.lower().removesuffix('.exe')
        if program in ('cd', 'set-location', 'pushd') and not (index and operators[index - 1] == '|'):
            target = [w for w in words[1:] if w.lower() not in ('-path', '-literalpath')]
            if len(target) != 1 or not readable(shell_path(target[0], base)):
                return False
            base = shell_path(target[0], base)
            continue
        if program in ('docker', 'podman'):
            if len(words) < 3 or words[1] != 'exec':
                return False
            continue  # Container-side arguments are interpreted inside the container.
        if program not in READ_ONLY:
            return False
        if any(w.startswith(WRITING_OPTIONS.get(program, ())) for w in words[1:]):
            return False
        if program == 'git' and not (len(words) > 1 and words[1] in GIT_READ or words[1:3] == ['worktree', 'list']):
            return False
        if program == 'sed':
            options = [w for w in words[1:] if w.startswith('-')]
            scripts = [w for w in words[1:] if not w.startswith('-')]
            if options != ['-n'] or not scripts or not re.fullmatch(r'\d+(?:,\d+)?p', scripts[0]):
                return False  # Print a line range only; no in-place edits or w/e commands.
        for word in words[1:]:
            for value in (word, word.split('=', 1)[1] if '=' in word else ''):
                pathlike = (value.startswith(('/', '\\', '~')) or re.match(r'[A-Za-z]:[\\/]', value)
                            or '..' in re.split(r'[\\/]', value))
                if pathlike and not readable(shell_path(value, base)):
                    return False
    return True


def evaluate(payload, *, cwd_is_execution_context=True):
    session_id = payload.get('session_id')
    if not session_id:
        return None  # No identity means no adoption or project discovery.
    try:
        binding = ownership.lookup(session_id)
    except (ValueError, OSError):
        return 'Veera session routing is invalid; do not access task state.'
    if binding is None:
        return None  # Critically: no cwd, ancestor, Git or run-state access.
    root = Path(binding['root'])
    cwd = Path(payload.get('cwd', '.')).resolve()
    original = None  # Set only when the host folder stays the recorded original checkout.
    if cwd_is_execution_context and not cwd.is_relative_to(root):
        # Desktop and delegated sessions keep their folder after `workspace`.
        # Only this owner's validated metadata can name that origin; any other
        # folder is still another project.
        try:
            capability = ownership.registry() / (ownership.session_key(session_id) + '.json')
            ownership.authorize(session_id, root, capability)
            original = original_checkout(root)
        except Exception:
            original = None
        if original is None or not inside(cwd, original):
            return 'This Veera session is bound to its task worktree ' + str(root) + '; do not operate in another project.'
    elif cwd_is_execution_context:
        # Nested repositories are separate projects even inside the owned path.
        for directory in [cwd, *cwd.parents]:
            if directory == root:
                break
            if (directory / '.git').exists():
                return 'Nested repository is not the owned Veera task.'
    try:
        capability = ownership.registry() / (ownership.session_key(session_id) + '.json')
        ownership.authorize(session_id, root, capability)
        run = status(root) if (root / STATE / 'state.json').exists() else {'status': 'preparing', 'contract': {'scope': []}}
    except Exception:
        return 'Owned Veera state is unavailable; no automatic adoption or repair.'
    tool = payload.get('tool_name', '')
    args = payload.get('tool_input', {})
    native_policy = os.environ.get('VEERA_HOST') in ('codex', 'dsh')
    if tool in ('Read', 'Glob', 'Grep'):
        target = args.get('file_path') or args.get('path') or str(cwd)
        path = (cwd / target).resolve()
        plugin = Path(__file__).resolve().parents[1]
        plugin_docs = (path.is_relative_to(plugin / 'docs') or path.is_relative_to(plugin / 'agents')
                       or path == plugin / 'README.md'
                       or path.is_relative_to(plugin / 'skills')
                       or path == plugin / 'adapters/codex/README.md'
                       or path.is_relative_to(plugin / 'adapters/codex/skills'))
        # The plugin's own package (docs and the rules in scripts/) is readable,
        # so a refused session can learn the accepted forms; nested repos are not.
        plugin_docs = plugin_docs or inside(path, plugin)
        if host_tool_output(path, session_id):
            return None  # The host's saved copy of this session's own long output.
        if not path.is_relative_to(root) and not plugin_docs:
            # The checkout this task was created from stays readable as context.
            origin = original if original is not None else original_checkout(root)
            if origin is not None and inside(path, origin):
                return None
            return 'Read/search target is outside this task; unrelated project context is not authorized.'
        if path.is_relative_to(root):
            for parent in [path if path.is_dir() else path.parent, *path.parents]:
                if parent == root:
                    break
                if (parent / '.git').exists():
                    return 'Nested project is outside the task read scope.'
        return None
    if tool == 'ListAgents':
        return 'Do not enumerate unrelated sessions; address only task agents by their recorded delegation IDs.'
    if tool == 'ToolSearch':
        return None
    if os.environ.get('VEERA_HOST') == 'codex' and tool in CODEX_CHAT_RECOVERY:
        # Communication remains subject to host/user authority. This neither
        # transfers task ownership nor grants permission to resume execution.
        return None
    if tool in ('Bash', 'PowerShell'):
        # One controller call, however the host passes identity to children, is
        # judged exactly like the bare call, on either shell.
        call, refusal, from_worktree, prefixed = controller_form(args.get('command', ''), root)
        if refusal:
            return refusal
        if prefixed and run['status'] in TERMINAL:
            return 'Veera run is ' + run['status'] + '; no further mutating/execution tools in this run. Inspect state using read-only tools.'
        if call is not None:
            if original is not None and not from_worktree:
                try:
                    relative = next(relative_inputs(shell_words(call)), None)
                except ValueError:
                    relative = None
                if relative:
                    # The shell resolves it in the original checkout, not the task.
                    return ('This shell starts in the original checkout, so ' + relative[0] + ' ' + relative[1] + ' would be read there; pass '
                            + relative[0] + ' "' + str(root / relative[1]) + '" or prefix the call with cd "' + str(root) + '" && .')
            tool, args = 'Bash', {**args, 'command': call}
    confined = tool in ('Bash', 'PowerShell') and (anchored(args.get('command', ''), root) or (
        original is not None and origin_command(args.get('command', ''), cwd, original, root)))
    controller = Path(__file__).resolve().parent / 'delivery.py'
    redirect = ('This session is bound to task worktree ' + str(root) + ' but its shell starts in the original checkout, which stays read-only. '
                'Anchor task commands: cd "' + str(root) + '" && <command> [&& <command>] [| head|tail|grep]; every path stays in the worktree, '
                'no $ or backtick substitution, no -c inline code; docker exec runs from either folder. '
                'Reads (ls, cat, grep, sed -n, git status/log/diff) also run unanchored. '
                'Run each controller call alone as: CLAUDE_PLUGIN_DATA="' + os.environ.get('CLAUDE_PLUGIN_DATA', '<plugin_data>')
                + '" VEERA_HOST=' + (os.environ.get('VEERA_HOST') or 'claude') + ' python3 "' + str(controller) + '" <subcommand> --root "'
                + str(root) + '" --session-id ' + session_id + ' --capability-file "' + str(capability) + '" ... '
                '(give --contract/--file as absolute worktree paths).')
    if tool == 'Bash':
        raw_command = args.get('command', '')
        try:
            words = shell_words(raw_command)
        except ValueError:
            return 'Cannot validate malformed shell command.'
        parsed_command = raw_command
        if os.name == 'nt' and raw_command.lstrip().startswith('&') and controller_command(words):
            parsed_command = raw_command.lstrip()[1:]
        lexer = shlex.shlex(parsed_command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        compound = any(t in (';', '&&', '||', '|', '&', '>', '>>', '<') for t in lexer) or '$(' in raw_command or '`' in raw_command or '\n' in raw_command
        if os.environ.get('VEERA_HOST') == 'codex' and not compound and '$' not in raw_command:
            # Deliberately small inspection grammar; arbitrary shell and tool
            # wrappers remain execution, including commands named like reads.
            if len(words) == 3 and words[:2] == ['Get-Content', '-LiteralPath'] and Path(words[2]).is_absolute():
                return evaluate({**payload, 'tool_name': 'Read', 'tool_input': {'file_path': words[2]}},
                                cwd_is_execution_context=cwd_is_execution_context)
            if (len(words) in (4, 5) and words[:2] == ['git', '-C']
                    and Path(words[2]).is_absolute() and Path(words[2]).resolve() == root
                    and words[3] == 'status' and (len(words) == 4 or words[4] in ('--short', '--porcelain'))):
                return None
        if compound and not native_policy and not confined:
            return redirect if original is not None else 'ASK:Compound shell execution requires explicit confinement review'
        # Parse owner options in any order; never let duplicates hide approval rules.
        owner_options = [('--session-id', session_id), ('--capability-file', str(capability))]
        if os.environ.get('VEERA_HOST') == 'codex':
            owner_options += [('--host', 'codex'), ('--plugin-data', os.environ.get('CLAUDE_PLUGIN_DATA', ''))]
        for flag, expected in owner_options:
            positions = [i for i, word in enumerate(words) if word == flag or word.startswith(flag + '=')]
            if len(positions) > 1:
                return 'Duplicate owner options are not allowed.'
            if positions:
                i = positions[0]
                if '=' in words[i]:
                    value = words[i].split('=', 1)[1]
                    del words[i]
                else:
                    if i + 1 >= len(words):
                        return 'Missing owner option value.'
                    value = words[i + 1]
                    del words[i:i + 2]
                if not expected or (shell_path(value, Path.cwd()) != Path(expected).resolve() if flag in ('--capability-file', '--plugin-data') else value != expected):
                    return 'Controller identity does not match the calling host session.'
        # Required approval is recognized independently of other argument order.
        script_path = str(Path(__file__).resolve().parent / 'delivery.py')
        if not compound and controller_command(words):
            if words[-1] in ('-h', '--help') and len(words) <= 4:
                return None  # Usage text only; argparse exits before any state is read.
            if words[2] in ('resume', 'amend', 'extend-repairs', 'correct-check-reporting', 'rebind-check-inputs', 'blocker-human-resolve'):
                if native_policy:
                    return None  # Controller validates identity, recorded user intent and state.
                return 'ASK:Explicit user approval is required for this authority-sensitive recovery operation'
        # Narrow escape hatch for reading/archiving finished state, never shell chains.
        script = str(Path(__file__).resolve().parent / 'delivery.py')
        if not compound and len(words) == 5 and controller_command(words) and words[2] in ('status', 'fingerprint', 'archive', 'context', 'unbind', 'dashboard-info') and words[3] == '--root' and shell_path(words[4], Path.cwd()) == root:
            return None
        if not compound and len(words) == 7 and controller_command(words) and words[2] == 'blocker-human-resolve' and words[3] == '--root' and shell_path(words[4], Path.cwd()) == root and words[5] == '--file':
            return 'ASK:Confirm the actual human-only blocker is resolved; agent advice cannot grant this authority'
        if not compound and len(words) == 7 and controller_command(words) and words[2] in ('checkpoint', 'resume') and words[3] == '--root' and shell_path(words[4], Path.cwd()) == root:
            expected = '--file' if words[2] == 'resume' else '--reason'
            if words[5] == expected:
                # Ask the host/user rather than authorize a hard-budget extension ourselves.
                return 'ASK:Explicit approval required to resume stopped work' if words[2] == 'resume' else None
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        target = args.get('file_path') or args.get('notebook_path')
        if target:
            resolved = (cwd / target).resolve()
            if resolved.is_relative_to(root):
                for parent in [resolved.parent, *resolved.parents]:
                    if parent == root:
                        break
                    if (parent / '.git').exists():
                        return 'Write target belongs to a nested project, not this task.'
    if run['status'] in TERMINAL and tool in ('Write', 'Edit'):
        name = args.get('file_path', '')
        path = (cwd / name).resolve()
        if path.is_relative_to(root / '.veera-artifacts'):
            return None  # Preserve blocker/authorization evidence, never source changes.
    if run['status'] in TERMINAL:
        return 'Veera run is ' + run['status'] + '; no further mutating/execution tools in this run. Inspect state using read-only tools.'
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        name = args.get('file_path') or args.get('notebook_path')
        if not name:
            return 'Veera cannot establish the write target.'
        path = (cwd / name).resolve()
        if not path.is_relative_to(root):
            origin = original if original is not None else original_checkout(root)
            if origin is not None and path.is_relative_to(origin):
                return ('Write target is in the original checkout, which stays read-only; edit '
                        + str(root / path.relative_to(origin)) + ' in the task worktree instead.')
            return 'Write target is outside the authorized repository.'
        relative = path.relative_to(root).as_posix()
        if any(part.lower() in ('.git', '.claude', '.codex', STATE) or part.lower().startswith('.env') or part.lower() in ('credentials.json', 'id_rsa', 'id_ed25519') for part in path.relative_to(root).parts):
            return 'Protected configuration, run state or secret file requires separate authorization.'
        if relative.startswith('.veera-artifacts/'):
            return None  # Evidence only; ignored source paths are never implementation scope.
        if not scoped(relative, run['contract']['scope']):
            if not (root / STATE / 'state.json').exists():
                return ('Source edits start after init: write the contract to ' + str(root / '.veera-artifacts' / 'contract.json')
                        + ' with this path in scope, run the controller init, then edit ' + str(path) + '.')
            return 'Write target is outside the frozen scope. PM must consult Architect/Advisor; do not silently expand scope.'
    if confined:
        return None  # Anchored in the owned worktree; terminal runs were refused above.
    if tool in ('Bash', 'PowerShell') and original is not None:
        if not (tool == 'Bash' and controller_command(shell_words(args.get('command', '')))):
            return redirect  # Never execute in the original checkout.
    if tool == 'Bash' and not native_policy:
        command = args.get('command', '')
        # Arbitrary shell can bypass path checks; require the host's approval,
        # rather than claiming this hook is a shell sandbox.
        try:
            tokens = shell_words(command)
        except ValueError:
            return 'Cannot validate malformed shell command.'
        script = str(Path(__file__).resolve().parent / 'delivery.py')
        if not controller_command(tokens):
            return 'ASK:Confirm this command is confined to the owned task and cannot affect another session/project'
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        if any(t in (';', '&&', '||', '|', '&', '>', '>>', '<') for t in lexer) or '$(' in command or '`' in command or '\n' in command:
            return 'ASK:Compound shell execution requires explicit confinement review'
        if DANGEROUS.search(command):
            return 'Destructive, publishing or infrastructure action is outside ordinary Build/Fix authorization.'
    if tool in ('Workflow', 'ScheduleWakeup', 'CronCreate'):
        return 'Veera does not authorize nested workflows or schedulers.'
    return None


def handle(payload, *, cwd_is_execution_context=True):
    # Classify only the exact host record before accessing any project state.
    try:
        if not isinstance(payload, dict):
            return {}
        key = ownership.session_key(payload.get('session_id'))
        path = ownership.registry() / (key + '.json')
        present = path.exists() or path.is_symlink()
    except (ValueError, OSError):
        return {}  # Unknown ownership cannot justify interfering with another session.
    if not present:
        from bootstrap import tool_context
        return tool_context(payload, os.environ.get('VEERA_HOST', 'claude'))
    try:
        reason = evaluate(payload, cwd_is_execution_context=cwd_is_execution_context)
    except Exception:
        reason = 'Owned Veera hook failed validation; controlled action denied.'
    if not reason:
        return {}
    decision = 'ask' if reason.startswith('ASK:') else 'deny'
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': decision, 'permissionDecisionReason': reason.removeprefix('ASK:')}}


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{}')
        return
    print(json.dumps(handle(payload)))


if __name__ == '__main__':
    main()
