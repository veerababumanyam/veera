"""Packaging checks for spec-driven Build guidance; not proof of agent behavior."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/build/SKILL.md'
STANDARDS = ROOT / 'docs/engineering-standards.md'


def section(text, heading):
    match = re.search(r'^## ' + re.escape(heading) + r'\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    return match.group(1) if match else ''


class BuildFlowTests(unittest.TestCase):
    def test_standards_define_spec_derived_tests(self):
        body = section(STANDARDS.read_text(encoding='utf-8'), 'Spec-derived tests').lower()
        self.assertTrue(body, 'missing Spec-derived tests section')
        for phrase in ('test oracle', 'criterion ledger', 'numbered invariant', 'concurrency', 'idempotency',
                       'persistence/restart', 'exact', 'first rejected value', 'terminal state',
                       'unchanged-on-failure', 'parallel requests', 'mutation probe', 'revert'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_spec_tests_never_contradict_a_conforming_reference(self):
        body = section(STANDARDS.read_text(encoding='utf-8'), 'Spec-derived tests').lower()
        for phrase in ('leaves open', 'tie order', "specification's sort key", 'public interface only',
                       'would fail on a conforming reference', 'no pinning test', 'rather than rerunning'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_reviewer_checks_the_ledger(self):
        routing = section(STANDARDS.read_text(encoding='utf-8'), 'Role routing')
        reviewer = next(line for line in routing.splitlines() if line.startswith('| Reviewer |'))
        self.assertIn('criterion ledger', reviewer)
        self.assertIn('unmapped IDs', reviewer)

    def test_skill_routes_written_specs_to_the_section(self):
        text = SKILL.read_text(encoding='utf-8')
        body = section(text, 'Spec-driven builds')
        self.assertTrue(body, 'missing Spec-driven builds section')
        self.assertIn('${CLAUDE_PLUGIN_ROOT}/docs/engineering-standards.md` section Spec-derived tests', body)
        self.assertIn('Spec-derived tests', STANDARDS.read_text(encoding='utf-8'))
        self.assertIn('follow Spec-driven builds below', section(text, 'Plan and implement'))
        self.assertLess(text.index('## Spec-driven builds'), text.index('## Verify, review, publish'))

    def test_skill_bounds_runs_and_post_review_churn(self):
        body = section(SKILL.read_text(encoding='utf-8'), 'Spec-driven builds')
        for phrase in ('criterion ledger', 'new test file alone', 'full suite once before review and once on the final tree',
                       'never rerun an unchanged suite', 'single independent reviewer', 'spec-backed defect',
                       'mutation probe', 'Never pin behavior the specification leaves open'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_skill_keeps_safety_and_size(self):
        text = SKILL.read_text(encoding='utf-8')
        for phrase in ('workspace --root ORIGINAL', 'local-verify', '`push_authorized: true` only with actual user authority',
                       'Self-review cannot satisfy this gate', 'never the original checkout'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertLessEqual(len(text.splitlines()), 100)
        numbers = [int(n) for n in re.findall(r'^(\d+)\. ', section(text, 'Plan and implement'), re.M)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))


if __name__ == '__main__':
    unittest.main()
