"""Packaging checks for bounded-cost spec-driven Build guidance; not proof of agent behavior."""
from pathlib import Path
import json
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import delivery  # noqa: E402

SKILL = ROOT / 'skills/build/SKILL.md'
STANDARDS = ROOT / 'docs/engineering-standards.md'


def section(text, heading, level='## '):
    match = re.search(r'^' + level + re.escape(heading) + r'\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    return match.group(1) if match else ''


def spec_section():
    return section(SKILL.read_text(encoding='utf-8'), 'Spec-driven builds')


def contract_template():
    match = re.search(r'`(\{"delivery_mode".*?\})`', spec_section())
    return json.loads(match.group(1)) if match else None


class BuildCostTests(unittest.TestCase):
    def test_lean_reading_list_skips_process_docs(self):
        body = spec_section()
        self.assertIn('Lean reading list', body)
        for doc in ('agent-contract.md', 'requirements-analysis.md', 'intake-and-autonomy.md', 'model-routing.md',
                    'dashboard.md', 'automatic-entry.md'):
            with self.subTest(doc=doc):
                self.assertIn(doc, body)
        self.assertIn('never grep runtime sources for formats', body)
        self.assertIn('never re-read a file you already have', body)
        text = SKILL.read_text(encoding='utf-8')
        for pointer in ('follows the lean reading list in Spec-driven builds instead',
                        'except for a spec-driven build', 'a spec-driven build omits both',
                        'a spec-driven build uses step 6 of Spec-driven builds instead'):
            with self.subTest(pointer=pointer):
                self.assertIn(pointer, text)

    def test_inline_contract_template_passes_runtime_validation(self):
        contract = contract_template()
        self.assertIsNotNone(contract, 'missing inline contract template')
        self.assertEqual(contract['delivery_mode'], 'local-verify')
        self.assertNotIn('release', contract)
        self.assertNotIn('discovery', contract)
        self.assertEqual([c['id'] for c in contract['checks']], ['suite'])
        with tempfile.TemporaryDirectory() as directory:
            delivery.validate_contract(contract, Path(directory).resolve())

    def test_template_count_pattern_reads_only_summary_lines(self):
        pattern = contract_template()['checks'][0]['count_pattern']
        for output in ('ok 1 - C3 pass 2 holds\n# tests 67\n# pass 67\n# fail 0\n',
                       '✔ C3 pass 2 holds\nℹ tests 67\nℹ pass 67\nℹ fail 0\n'):
            with self.subTest(output=output[:12]):
                self.assertEqual(sum(int(x) for x in re.findall(pattern, output)), 67)

    def test_steps_batch_calls_and_bound_loops(self):
        body = spec_section()
        numbers = [int(n) for n in re.findall(r'^(\d+)\. ', body, re.M)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        for phrase in ('Setup in three calls', 'One `test` check', 'criteria are the ledger IDs',
                       'phases are strictly ordered', 'never by polling or reading its output file',
                       'one scripted Bash pass over all chosen mutants', 'Finish README/docs edits before verify',
                       'forces a new check and review', 'does not rerun the full suite', 'at most one repair round',
                       'not into another loop', 'untracked new files', 'when review changes nothing it is also the final-tree run'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_review_shape_matches_runtime_import(self):
        body = spec_section()
        shape = re.search(r'review file shape `\{(.*?)\}`', body)
        self.assertIsNotNone(shape)
        for field in ('reviewer', 'approved', 'criteria', 'fingerprint', 'notes'):
            with self.subTest(field=field):
                self.assertIn('"' + field + '"', shape.group(1))
                self.assertIn("'" + field + "'", (ROOT / 'scripts/delivery.py').read_text(encoding='utf-8'))

    def test_bound_session_avoids_refused_shell_forms(self):
        body = spec_section()
        for phrase in ('git diff --output=PATH', 'no shell redirects or deletes', '`.veera-artifacts/`'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_standards_bound_cost_without_dropping_quality(self):
        body = section(STANDARDS.read_text(encoding='utf-8'), 'Spec-derived tests')
        for phrase in ('Bounded cost.', 'ledger and the mutation probe', 'full suite once as the frozen check',
                       'one reviewer pass', 'at most one repair round', 'Criterion ledger', 'Mutation probe'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_safety_kept_and_skill_stays_small(self):
        text = SKILL.read_text(encoding='utf-8')
        for phrase in ('workspace --root ORIGINAL', 'never the original checkout', 'Self-review cannot satisfy this gate',
                       '`push_authorized: true` only with actual user authority', 'single independent reviewer'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertLessEqual(len(text.splitlines()), 100)


if __name__ == '__main__':
    unittest.main()
