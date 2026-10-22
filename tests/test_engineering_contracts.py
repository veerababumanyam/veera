"""Packaging checks for shared guidance; not proof of agent behavior."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EngineeringContractsTests(unittest.TestCase):
    def test_shared_standard_exists_and_is_stack_aware(self):
        text = (ROOT / 'docs/engineering-standards.md').read_text(encoding='utf-8')
        self.assertRegex(text.lower(), r'stack|language|framework')
        for topic in ('correctness', 'boundaries', 'simplicity', 'operability'):
            self.assertIn(topic, text.lower())

    def test_hygiene_requires_ownership_and_preservation(self):
        text = (ROOT / 'docs/engineering-standards.md').read_text(encoding='utf-8').lower()
        for phrase in ('repository hygiene and resource ownership', 'task-owned', 'shared caches', 'symlink', 'rollback', 'ram/cpu', 'one verified final delivery'):
            self.assertIn(phrase, text)

    def test_frontend_standard_preserves_accessible_central_design(self):
        text = (ROOT / 'docs/engineering-standards.md').read_text(encoding='utf-8')
        for phrase in ('Central design system first', 'WCAG 2.2 AA', 'keyboard', 'touch', 'ECharts', 'table alternatives', 'reduced-motion', 'not replace'):
            self.assertIn(phrase, text)

    def test_build_and_fix_reference_shared_standard(self):
        for mode in ('build', 'fix'):
            with self.subTest(mode=mode):
                text = (ROOT / 'skills' / mode / 'SKILL.md').read_text(encoding='utf-8')
                self.assertIn('engineering-standards.md', text)
                self.assertLessEqual(len(text.splitlines()), 100)

    def test_all_existing_roles_reference_shared_standard(self):
        for path in sorted((ROOT / 'agents').glob('*.md')):
            with self.subTest(role=path.stem):
                self.assertIn('engineering-standards.md', path.read_text(encoding='utf-8'))

    def test_shared_contract_references_standard(self):
        self.assertIn('engineering-standards.md', (ROOT / 'docs/agent-contract.md').read_text(encoding='utf-8'))

    def test_local_document_references_resolve(self):
        files = list((ROOT / 'agents').glob('*.md')) + list((ROOT / 'skills').glob('*/SKILL.md'))
        for path in files:
            for reference in re.findall(r'\$\{CLAUDE_PLUGIN_ROOT\}/(docs/[A-Za-z0-9_.-]+\.md)', path.read_text(encoding='utf-8')):
                with self.subTest(file=path.name, reference=reference):
                    self.assertTrue((ROOT / reference).is_file())


if __name__ == '__main__':
    unittest.main()
