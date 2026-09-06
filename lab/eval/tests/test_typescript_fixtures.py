"""The harness offline corpus is reviewable and never starts a paid judge."""
import json
from pathlib import Path

import pytest

from lab.eval.generate_evals import DOMAIN_CHECKS, generate_eval
from lab.eval.triggers import generate_triggers

ROOT = Path(__file__).resolve().parents[3]


def test_offline_generation_covers_all_skills_without_subprocess(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline fixture generation invoked an external process')
    monkeypatch.setattr(generate_triggers.subprocess, 'run', forbidden)
    descriptions = generate_triggers.get_all_skill_descriptions()
    assert len(descriptions) == 51
    assert set(descriptions) == set(DOMAIN_CHECKS) == set(generate_triggers.CURATED_POSITIVES)
    for name, description in descriptions.items():
        corpus = generate_triggers.generate_for_skill(name, description, descriptions)
        assert corpus == generate_triggers.generate_for_skill(name, description, descriptions)
        positive = corpus['should_trigger'] + corpus['should_trigger_test']
        negative = corpus['should_not_trigger']
        assert len(positive) == len(set(positive)) == 7
        assert len(negative) == len(set(negative)) == 5
        assert not set(positive).intersection(negative)
        assert all('/ts:' not in prompt and 'should trigger' not in prompt.lower() for prompt in positive + negative)


def test_new_skill_requires_authored_routing_cases():
    with pytest.raises(ValueError, match='No authored TypeScript trigger cases'):
        generate_triggers.generate_for_skill('unknown-skill', 'Unknown behavior', {'unknown-skill': 'Unknown behavior'})


def test_semantic_eval_requirements_survive_generation(tmp_path):
    # A superficially well-structured empty technology guide must still receive
    # real contract, domain and persistence requirements in its generated eval.
    path = tmp_path / 'SKILL.md'
    path.write_text('---\nname: domain-resources\ndescription: Use when designing a domain resource across TypeScript packages.\n---\n# Domain\n\n## Iron Laws\n1. Read rules.\n2. Verify.\n3. Preserve scope.\n')
    generated = generate_eval('domain-resources', str(path))
    patterns = [check.get('pattern', '') for check in generated['dimensions']['completeness']['checks']]
    assert 'TypeBox' in patterns and 'service' in patterns and 'repositor' in patterns
    assert generated['dimensions']['safety']['weight'] == .08
    assert generated['dimensions']['behavioral']['weight'] == .20


def test_all_canonical_skills_have_dedicated_evals():
    skills = {path.parent.name for path in (ROOT / 'plugins/typescript-starter/skills').glob('*/SKILL.md')}
    files = {path.stem: path for path in (ROOT / 'lab/eval/evals').glob('*.json') if not path.stem.startswith('_')}
    assert skills == files.keys() == DOMAIN_CHECKS.keys()
    assert 'codex-loop' in files
    for name, path in files.items():
        data = json.loads(path.read_text())
        assert data['skill'] == name
        checks = data['dimensions']['completeness']['checks']
        actual = {(check.get('pattern'), check.get('desc')) for check in checks if check['type'] == 'content_present'}
        assert set(DOMAIN_CHECKS[name]).issubset(actual)
