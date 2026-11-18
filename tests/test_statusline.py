"""Regression coverage for payload interpretation and safe installation."""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load('statusline')
installer = load('install')


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = pathlib.Path(self.temp.name)
        patch = unittest.mock.patch.dict(os.environ, {'BETTER_STATUSLINE_CAVEMAN': '0', 'ASM_HOME': str(self.home / 'asm')}, clear=True)
        patch.start()
        self.addCleanup(patch.stop)
        renderer.CLAUDE = self.home

    def render(self, payload, harness='claude'):
        renderer.HARNESS = harness
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            renderer.main(payload)
        return re.sub(r'\x1b\[[0-9;]*m', '', output.getvalue())

    def test_claude_uses_current_prompt_not_cumulative_tokens(self):
        output = self.render({'model': {'display_name': 'Opus 5.5'}, 'effort': {'level': 'medium'}, 'context_window': {'current_usage': {'input_tokens': 165000, 'cache_read_input_tokens': 10000}, 'total_input_tokens': 5000000, 'context_window_size': 1000000}})
        self.assertIn('Effort: medium', output)
        self.assertIn('Ctx: 17% (175k/1M)', output)

    def test_cursor_session_percentage_wins_over_last_call(self):
        output = self.render({'model': {'display_name': 'Composer', 'param_summary': '(High)'}, 'context_window': {'used_percentage': 72.5, 'total_input_tokens': 145000, 'current_usage': {'input_tokens': 291000}, 'context_window_size': 200000}}, 'cursor')
        self.assertIn('Effort: High', output)
        self.assertIn('Ctx: 72% (145k/200k)', output)
        self.assertNotIn('Cost:', output)

    def test_cursor_reads_selected_model_effort_only_for_matching_model(self):
        config = self.home / 'cli-config.json'
        config.write_text(json.dumps({'selectedModel': {'modelId': 'composer', 'parameters': [{'id': 'effort', 'value': 'high'}]}}))
        with unittest.mock.patch.dict(os.environ, {'CURSOR_CONFIG_PATH': str(config)}):
            self.assertIn('Effort: high', self.render({'model': {'id': 'composer'}}, 'cursor'))
            self.assertIn('Effort: auto', self.render({'model': {'id': 'other'}}, 'cursor'))

    def test_antigravity_effort_quota_rounding_and_conversation_id(self):
        output = self.render({'model': {'id': 'carbon', 'display_name': 'Gemini 4 Carbon (Medium)'}, 'quota': {'carbon': {'remaining_fraction': 0.8, 'reset_in_seconds': 3600}}, 'conversation_id': 'agy-id'}, 'antigravity')
        self.assertIn('Model: Gemini 4 Carbon | Effort: medium | Quota: 20% (1h0m)', output)
        self.assertIn('Session: agy-id', output)

    def test_quota_matches_model_and_does_not_guess_another_models_limit(self):
        payload = {'model': {'id': 'b'}, 'quota': {'a': {'used_percentage': 90}, 'b': {'used_percentage': 25}}}
        self.assertIn('Quota: 25%', self.render(payload, 'antigravity'))
        payload['model']['id'] = 'c'
        self.assertNotIn('Quota:', self.render(payload, 'antigravity'))

    def test_unknown_metrics_are_hidden_but_real_zero_is_displayed(self):
        self.assertNotIn('Cost:', self.render({}))
        self.assertNotIn('5h:', self.render({}))
        output = self.render({'cost': {'total_cost_usd': 0}, 'rate_limits': {'five_hour': {'used_percentage': 0}}})
        self.assertIn('Cost: $0', output)
        self.assertIn('5h: 0%', output)

    def test_compaction_setting_is_claude_only(self):
        (self.home / 'settings.json').write_text('{"autoCompactWindow":600000}')
        payload = {'context_window': {'used_percentage': 10, 'context_window_size': 1000000}}
        self.assertIn('compact @600k', self.render(payload))
        self.assertNotIn('compact @', self.render(payload, 'cursor'))
        self.assertNotIn('compact @', self.render(payload, 'antigravity'))

    def test_caveman_reads_bounded_flag_and_suffix_without_spawning(self):
        (self.home / '.caveman-active').write_text('full\n')
        (self.home / '.caveman-statusline-suffix').write_text('saved 25%')
        with unittest.mock.patch.dict(os.environ, {'BETTER_STATUSLINE_CAVEMAN': ''}), unittest.mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('child process')):
            self.assertIn('[CAVEMAN] saved 25%', self.render({}))

    def test_caveman_refuses_symlink_and_terminal_controls(self):
        flag = self.home / '.caveman-active'
        other = self.home / 'other'
        other.write_text('full')
        flag.symlink_to(other)
        with unittest.mock.patch.dict(os.environ, {'BETTER_STATUSLINE_CAVEMAN': ''}):
            self.assertNotIn('CAVEMAN', self.render({}))
        self.assertNotIn('\x1b]52', self.render({'model': {'display_name': '\x1b]52;bad\x07'}}))

    def test_custom_caveman_override_remains_bounded(self):
        script = self.home / 'badge.sh'
        script.write_text('sleep 20 &\nwait\nprintf bad')
        with unittest.mock.patch.dict(os.environ, {'BETTER_STATUSLINE_CAVEMAN': str(script)}):
            self.assertNotIn('bad', self.render({}))
        script.write_text('printf custom')
        with unittest.mock.patch.dict(os.environ, {'BETTER_STATUSLINE_CAVEMAN': str(script)}):
            self.assertIn('custom', self.render({}))

    def test_workflow_cache_path_and_stages(self):
        asm = self.home / 'asm'
        (asm / 'sessions').mkdir(parents=True)
        (asm / 'sessions/session').write_text('PLAN\nDEV\n')
        machine = {'states': [{'name': 'PLAN', 'color': 141}, {'name': 'DEV', 'color': 39}, {'name': 'DONE', 'color': 82}], 'statusline': {'style': 'path'}}
        (asm / 'machine.json').write_text(json.dumps(machine))
        self.assertIn('PLAN ›  DEV ', self.render({'session_id': 'session'}))
        machine['statusline']['style'] = 'stages'
        (asm / 'machine.json').write_text(json.dumps(machine))
        self.assertIn('✓ PLAN ›  DEV  › DONE', self.render({'session_id': 'session'}))

    def test_entrypoint_accepts_empty_null_and_invalid_json(self):
        for raw in ('{}', 'null', 'invalid'):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/statusline.py')], input=raw, text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='statusline with spaces ')
        self.addCleanup(self.temp.cleanup)
        self.home = pathlib.Path(self.temp.name)
        patch = unittest.mock.patch.dict(os.environ, {'HOME': str(self.home)}, clear=True)
        patch.start()
        self.addCleanup(patch.stop)

    def install(self, harness, force=False):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return installer.install(harness, force)

    def test_all_harnesses_install_persistent_independent_commands(self):
        for harness, name in [('claude', '.claude/settings.json'), ('cursor', '.cursor/cli-config.json'), ('antigravity', '.gemini/antigravity-cli/settings.json')]:
            self.assertEqual(self.install(harness), 0)
            path = self.home / name
            data = json.loads(path.read_text())
            self.assertIn('statusline.py', data['statusLine']['command'])
            result = subprocess.run(data['statusLine']['command'], shell=True, input='{}', capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Model:', result.stdout)
            before = path.read_bytes()
            self.assertEqual(self.install(harness), 0)
            self.assertEqual(before, path.read_bytes())
            if harness == 'cursor':
                self.assertGreaterEqual(data['statusLine']['timeoutMs'], 5000)
                self.assertEqual(data['permissions'], {'allow': [], 'deny': []})
            if harness == 'antigravity':
                self.assertTrue(data['statusLine']['enabled'])

    def test_existing_custom_command_needs_force_and_is_backed_up(self):
        path = self.home / '.claude/settings.json'
        path.parent.mkdir()
        original = {'env': {'KEEP': 'yes'}, 'statusLine': {'type': 'command', 'command': 'custom', 'padding': 4}}
        path.write_text(json.dumps(original))
        self.assertEqual(self.install('claude'), 2)
        self.assertEqual(json.loads(path.read_text()), original)
        self.assertFalse((path.parent / 'better-ai-status-line').exists())
        self.assertEqual(self.install('claude', True), 0)
        updated = json.loads(path.read_text())
        self.assertEqual(updated['env'], original['env'])
        self.assertEqual(updated['statusLine']['padding'], 4)
        backup = next(path.parent.glob('settings.json.bak-*'))
        self.assertEqual(json.loads(backup.read_text()), original)

    def test_upgrade_from_shell_renderer_or_asm_keeps_workflow_history(self):
        path = self.home / '.claude/settings.json'
        path.parent.mkdir()
        asm = self.home / '.ai-state-machine'
        (asm / 'sessions').mkdir(parents=True)
        (asm / 'sessions/session').write_text('DEV\n')
        (asm / 'wrapped-statusline').write_text('existing command\n')
        path.write_text(json.dumps({'statusLine': {'command': 'bash "%s/bin/asm" statusline' % asm}}))
        self.assertEqual(self.install('claude'), 0)
        self.assertEqual((asm / 'sessions/session').read_text(), 'DEV\n')
        self.assertEqual((asm / 'wrapped-statusline').read_text(), 'existing command\n')
        path.write_text(json.dumps({'statusLine': {'command': 'bash "%s/better-ai-status-line/statusline.sh"' % path.parent}}))
        self.assertEqual(self.install('claude'), 0)

    def test_malformed_settings_are_not_overwritten(self):
        path = self.home / '.claude/settings.json'
        path.parent.mkdir()
        path.write_text('bad json')
        with self.assertRaises(ValueError):
            self.install('claude')
        self.assertEqual(path.read_text(), 'bad json')


if __name__ == '__main__':
    unittest.main()
