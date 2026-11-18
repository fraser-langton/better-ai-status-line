#!/usr/bin/env python3
"""Install the shared renderer without touching unrelated CLI settings."""
import argparse
import json
import os
import pathlib
import shlex
import shutil
import sys
import tempfile
import time


def install(harness, force=False):
    home = pathlib.Path.home()
    if harness == 'claude':
        config = pathlib.Path(os.environ.get('CLAUDE_CONFIG_DIR', str(home / '.claude')))
        settings_name = 'settings.json'
    elif harness == 'cursor':
        config = pathlib.Path(os.environ.get('CURSOR_CONFIG_DIR', str(home / '.cursor')))
        if os.environ.get('CURSOR_CONFIG_PATH'):
            config = pathlib.Path(os.environ['CURSOR_CONFIG_PATH']).parent
            settings_name = pathlib.Path(os.environ['CURSOR_CONFIG_PATH']).name
        else:
            settings_name = 'cli-config.json'
    else:
        config = pathlib.Path(os.environ.get('GEMINI_CONFIG_DIR', str(home / '.gemini/antigravity-cli')))
        settings_name = 'settings.json'
    settings = config / settings_name
    data = json.loads(settings.read_text()) if settings.is_file() else (
        {'version': 1, 'permissions': {'allow': [], 'deny': []}} if harness == 'cursor' else {})
    if not isinstance(data, dict) or not isinstance(data.get('statusLine', {}), dict):
        raise ValueError('settings and statusLine must be JSON objects')
    statusline = data.get('statusLine', {})
    current = statusline.get('command', '')
    target_dir = config / 'better-ai-status-line'
    target = target_dir / 'statusline.py'
    command = shlex.join([sys.executable, str(target), harness])
    asm_home = pathlib.Path(os.environ.get('ASM_HOME', str(home / '.ai-state-machine')))
    try:
        parts = shlex.split(current)
    except ValueError:
        parts = []
    # Recognise commands this package owns and ASM's wrapper, so upgrading is safe.
    owned = str(target) in parts or str(target_dir / 'statusline.sh') in parts
    wrapped = str(asm_home / 'bin/asm') in parts and 'statusline' in parts
    if current and current != command and not (owned or wrapped or force):
        print('%s already has a status line:\n  %s\nRe-run with --force to replace it (backed up first).' % (settings, current), file=sys.stderr)
        return 2
    here = pathlib.Path(__file__).resolve().parent
    config.mkdir(parents=True, exist_ok=True)
    updated = dict(statusline, type='command', command=command)
    updated.setdefault('padding', 2)
    if harness == 'antigravity':
        updated['enabled'] = True
    if harness == 'cursor':
        updated['timeoutMs'] = max(updated.get('timeoutMs', 0), 5000)
        updated['updateIntervalMs'] = max(updated.get('updateIntervalMs', 0), 1000)
    changed = updated != statusline
    if changed and settings.exists():
        backup = settings.with_name(settings.name + '.bak-' + str(time.time_ns()))
        shutil.copy2(settings, backup)
        print('Backup: %s' % backup)
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in ('statusline.py', 'statusline.sh'):
        source, dest = here / name, target_dir / name
        if source.resolve() != dest.resolve():
            shutil.copy2(source, dest)
    if changed or not settings.exists():
        data['statusLine'] = updated
        # Same-directory replacement keeps readers from seeing partial JSON.
        fd, temporary = tempfile.mkstemp(prefix=settings.name + '.', dir=config)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(data, stream, indent=2)
                stream.write('\n')
            if settings.exists():
                shutil.copymode(settings, temporary)
            os.replace(temporary, settings)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    print('Installed: %s\nSettings: %s' % (target, settings))
    if wrapped:
        print('Workflow progress reads the existing ASM cache directly; ASM hooks and history are unchanged.')
    print('Restart %s CLI to load the status line.' % harness)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', choices=('claude', 'cursor', 'antigravity'), default='claude')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--codex', action='store_true', help='print the native Codex [tui] configuration')
    args = parser.parse_args()
    if args.codex:
        print((pathlib.Path(__file__).resolve().parent.parent / 'codex/config.toml').read_text(), end='')
        return 0
    try:
        return install(args.harness, args.force)
    except (OSError, ValueError, TypeError) as error:
        print('Installation failed: %s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
