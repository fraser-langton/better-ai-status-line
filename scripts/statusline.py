#!/usr/bin/env python3
"""Shared statusline renderer; no child processes in the default path."""
import json
import math
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

HOME = pathlib.Path.home()
HARNESS = 'claude'
CLAUDE = pathlib.Path(os.environ.get('CLAUDE_CONFIG_DIR', str(HOME / '.claude')))


def read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def clean(value):
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(value))


def color(value, code):
    return '\033[38;5;%sm%s\033[0m' % (code, clean(value))


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def pct_color(value):
    return 196 if value >= 80 else 220 if value >= 50 else 82


def tokens(value):
    if value >= 1000000:
        return ('%.1f' % (value / 1000000)).rstrip('0').rstrip('.') + 'M'
    return '%dk' % (value // 1000) if value >= 1000 else str(int(value))


def reset(seconds):
    seconds = max(0, int(seconds))
    if not seconds:
        return 'now'
    if seconds < 60:
        return '%ds' % seconds
    if seconds < 3600:
        return '%dm' % (seconds // 60)
    if seconds < 86400:
        return '%dh%dm' % (seconds // 3600, seconds % 3600 // 60)
    return '%dd%dh' % (seconds // 86400, seconds % 86400 // 3600)


def read_short(path):
    with path.open(errors='replace') as stream:
        return stream.read(64)


def caveman_badge():
    custom = os.environ.get('BETTER_STATUSLINE_CAVEMAN')
    if custom == '0':
        return ''
    if custom:
        # An explicit custom script is the only optional child process. Bound it
        # so a slow badge cannot consume the CLI's entire redraw deadline.
        try:
            process = subprocess.Popen(['bash', custom], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True)
            try:
                output, _ = process.communicate(timeout=0.25)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                return ''
            text = clean(re.sub(r'\x1b\[[0-9;]*m', '', output))
            return ' ' + color(text, 172) if text else ''
        except OSError:
            return ''
    flag = CLAUDE / '.caveman-active'
    if flag.is_symlink():
        return ''
    try:
        mode = re.sub('[^a-z0-9-]', '', read_short(flag).lower())
        if mode not in ('off', 'lite', 'full', 'ultra', 'wenyan-lite', 'wenyan', 'wenyan-full', 'wenyan-ultra', 'commit', 'review', 'compress'):
            return ''
        badge = ' ' + color('[CAVEMAN' + ('' if mode == 'full' else ':' + mode.upper()) + ']', 172)
        suffix = CLAUDE / '.caveman-statusline-suffix'
        if os.environ.get('CAVEMAN_STATUSLINE_SAVINGS') != '0' and not suffix.is_symlink() and suffix.is_file():
            badge += ' ' + color(clean(read_short(suffix)), 172)
        return badge
    except OSError:
        return ''


def workflow(data):
    """Read ASM's existing cache; leave transitions and history to ASM hooks."""
    sid = data.get('session_id') or data.get('conversation_id') or os.environ.get('ASM_SESSION_ID') or os.environ.get('CLAUDE_CODE_SESSION_ID') or os.environ.get('CODEX_THREAD_ID')
    if not sid:
        return
    asm_home = pathlib.Path(os.environ.get('ASM_HOME', str(HOME / '.ai-state-machine')))
    try:
        lines = (asm_home / 'sessions' / str(sid).replace('/', '_')).read_text().splitlines()
    except OSError:
        return
    history = [line.split('\t', 1) for line in lines if line]
    if not history:
        return
    cwd = pathlib.Path((data.get('workspace') or {}).get('current_dir') or data.get('cwd') or os.getcwd())
    candidates = [pathlib.Path(os.environ['ASM_MACHINE'])] if os.environ.get('ASM_MACHINE') else []
    candidates += [d / '.ai-state-machine/machine.json' for d in [cwd, *cwd.parents]]
    candidates += [asm_home / 'machine.json', asm_home / 'machine.default.json']
    machine = next((read_json(p) for p in candidates if p.is_file()), {})
    colors = {state['name']: state.get('color', 244) for state in machine.get('states', [])}
    current = history[-1][0]
    options = machine.get('statusline') or {}
    items = []
    if options.get('style') == 'stages':
        names = list(colors)
        visited = {entry[0] for entry in history}
        far = max((i for i, name in enumerate(names) if name in visited), default=-1)
        for i, name in enumerate(names):
            if name == current:
                items.append('\033[1;7;38;5;%sm %s \033[0m' % (colors[name], clean(name)))
            else:
                items.append(color(('✓ ' if name in visited else '✗ ' if i < far else '') + name, colors[name] if name in visited else 196 if i < far else 240))
    else:
        maximum = options.get('max', 12)
        maximum = maximum if isinstance(maximum, int) and maximum > 0 else 12
        if len(history) > maximum:
            items.append(color('+' + str(len(history) - maximum), 240))
        for i, entry in enumerate(history[-maximum:]):
            name = entry[0]
            prefix = color('✗ ', 196) if len(entry) > 1 and entry[1] == '0' and items else ''
            if i == len(history[-maximum:]) - 1:
                items.append(prefix + '\033[1;7;38;5;%sm %s \033[0m' % (colors.get(name, 244), clean(name)))
            else:
                items.append(prefix + color(name, colors.get(name, 244)))
    print(color(' › ', 240).join(items))


def main(data):
    model_data = data.get('model') or {}
    if isinstance(model_data, str):
        model_data = {'display_name': model_data}
    model = model_data.get('display_name') or model_data.get('id') or '?'
    effort = data.get('reasoning_effort') or data.get('effort')
    if isinstance(effort, dict):
        effort = effort.get('level')
    effort = effort or model_data.get('param_summary', '').strip(' ()')
    if not effort and HARNESS == 'cursor':
        cursor_dir = pathlib.Path(os.environ.get('CURSOR_CONFIG_DIR', str(HOME / '.cursor')))
        selected = read_json(pathlib.Path(os.environ.get('CURSOR_CONFIG_PATH', str(cursor_dir / 'cli-config.json')))).get('selectedModel', {})
        if selected.get('modelId') == model_data.get('id'):
            effort = ' '.join(str(p['value']) for p in selected.get('parameters', [])
                              if p.get('id') in ('effort', 'reasoning', 'reasoning_effort', 'thought_level', 'thinking') and p.get('value'))
    if not effort:
        match = re.search(r'\((low|medium|high|xhigh|max)\)', model, re.I)
        effort = match.group(1).lower() if match else 'max' if model_data.get('max_mode') else 'auto'
    if HARNESS == 'antigravity':
        model = re.sub(r'\s*\((low|medium|high|xhigh|max)\)\s*$', '', model, flags=re.I)
    lowered = model.lower()
    model_color = 82 if any(s in lowered for s in ('haiku', 'flash')) else 220 if any(s in lowered for s in ('sonnet', 'pro')) else 196 if any(s in lowered for s in ('opus', 'fable', 'ultra')) else 244
    parts = ['Model: ' + color(model, model_color), 'Effort: ' + color(effort, {'low': 82, 'medium': 37, 'high': 220, 'xhigh': 208, 'max': 196}.get(str(effort).lower(), 244))]
    limits = data.get('rate_limits') or {}
    for key, label in [('five_hour', '5h'), ('seven_day', '7d')]:
        limit = limits.get(key) or {}
        pct = limit.get('used_percentage')
        if number(pct):
            text = label + ': ' + color('%d%%' % pct, pct_color(pct))
            if number(limit.get('resets_at')) and limit['resets_at'] > 0:
                text += ' (' + reset(limit['resets_at'] - time.time()) + ')'
            parts.append(text)
    if not any(number((limits.get(k) or {}).get('used_percentage')) for k in ('five_hour', 'seven_day')):
        quota = data.get('quota') or {}
        if isinstance(quota, dict):
            model_id = model_data.get('id')
            q = quota.get(model_id) or (next(iter(quota.values())) if len(quota) == 1 else {})
            if isinstance(q, dict):
                pct = q.get('used_percentage')
                if not number(pct) and number(q.get('remaining_fraction')):
                    pct = round((1 - q['remaining_fraction']) * 100, 8)
                if number(pct):
                    text = 'Quota: ' + color('%d%%' % pct, pct_color(pct))
                    secs = q.get('reset_in_seconds')
                    if not number(secs) and number(q.get('resets_at')):
                        secs = q['resets_at'] - time.time()
                    if number(secs) and secs > 0:
                        text += ' (' + reset(secs) + ')'
                    parts.append(text)
    cost = data.get('cost')
    if isinstance(cost, dict):
        cost = cost.get('total_cost_usd')
    if number(cost):
        parts.append('Cost: ' + color('$' + ('%.2f' % cost).rstrip('0').rstrip('.'), 196 if cost >= 5 else 220 if cost >= 1 else 82))
    ctx = data.get('context_window') or {}
    used = ctx.get('used_percentage')
    window = ctx.get('context_window_size')
    usage = ctx.get('current_usage')
    total = None
    if HARNESS == 'claude' and isinstance(usage, dict):
        total = sum(usage.get(k) or 0 for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
        if number(window) and window > 0:
            used = total * 100 / window
    elif number(used) and number(window):
        total = used * window / 100
    elif number(ctx.get('total_input_tokens')):
        total = ctx['total_input_tokens']
    if not number(used) and number(total) and number(window) and window > 0:
        used = total * 100 / window
    if number(used):
        text = 'Ctx: ' + color('%d%%' % used, pct_color(used))
        if number(total) and number(window) and window > 0:
            text += ' (' + tokens(total) + '/' + tokens(window)
            compact = read_json(CLAUDE / 'settings.json').get('autoCompactWindow') if HARNESS == 'claude' else None
            if number(compact) and compact < window:
                text += ', compact @' + tokens(compact)
            text += ')'
        parts.append(text)
    badge = caveman_badge()
    print(' | '.join(parts) + badge)
    ids = []
    for label, value in [('Session', data.get('conversation_id') or data.get('session_id')), ('Superset ws', os.environ.get('SUPERSET_WORKSPACE_ID')), ('term', os.environ.get('SUPERSET_TERMINAL_ID'))]:
        if value:
            ids.append(label + ': ' + color(value, 103))
    if ids:
        print(' | '.join(ids))
    workflow(data)


if __name__ == '__main__':
    HARNESS = sys.argv[1] if len(sys.argv) > 1 else 'claude'
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    main(payload if isinstance(payload, dict) else {})
