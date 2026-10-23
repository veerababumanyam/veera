"""Validate a bounded, traceable requirements brief; never attest research or consent."""
import json
import re


def append(value, additions):
    """Append an authorized amendment without replacing any original discovery."""
    allowed = {'evidence', 'requirements', 'assumptions', 'non_goals', 'questions', 'plan'}
    if not isinstance(value, dict) or not isinstance(additions, dict) or not additions or not set(additions) <= allowed:
        raise ValueError('Discovery amendment needs an existing brief and append-only fields')
    if any(not isinstance(entries, list) for entries in additions.values()):
        raise ValueError('Discovery amendment fields must be lists')
    return {key: item + additions.get(key, []) if key in allowed else item for key, item in value.items()}


def validate(value, criteria, checks):
    def need(condition, message):
        if not condition:
            raise ValueError('Discovery: ' + message)

    def fields(item, names):
        need(isinstance(item, dict) and set(item) == set(names.split()), 'use the documented fields only')

    def text(item):
        need(isinstance(item, str) and bool(item.strip()) and len(item) <= 2000, 'text must be nonempty and at most 2000 characters')

    def items(item, minimum=0):
        need(isinstance(item, list) and minimum <= len(item) <= 30, 'lists must contain at most 30 entries')

    def identifier(item, seen):
        need(isinstance(item, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', item) and item not in seen, 'invalid or duplicate ID')
        seen.add(item)

    def refs(item, allowed):
        items(item, 1)
        need(all(isinstance(ref, str) for ref in item), 'references must be IDs')
        need(len(set(item)) == len(item) and set(item) <= allowed, 'unknown or duplicate reference')

    fields(value, 'version request outcome domain evidence requirements assumptions non_goals questions plan open_questions')
    need(type(value['version']) is int and value['version'] == 1, 'unsupported version')
    for key in ('request', 'outcome', 'domain'):
        text(value[key])
    for key in ('evidence', 'requirements', 'plan'):
        items(value[key], 1)
    for key in ('assumptions', 'non_goals', 'questions', 'open_questions'):
        items(value[key])
    need(not value['open_questions'], 'resolve essential questions before implementation')
    for key in ('assumptions', 'non_goals'):
        for item in value[key]:
            text(item)
    evidence_ids, kinds = set(), set()
    for item in value['evidence']:
        fields(item, 'id kind source finding')
        identifier(item['id'], evidence_ids)
        need(isinstance(item['kind'], str) and item['kind'] in ('user-request', 'code', 'documentation', 'external', 'observation'), 'unknown evidence kind')
        kinds.add(item['kind'])
        text(item['source'])
        text(item['finding'])
    need('user-request' in kinds and bool(kinds - {'user-request'}), 'include the user request and inspected project/research evidence')
    requirement_ids, covered = set(), set()
    for item in value['requirements']:
        fields(item, 'id text basis evidence_ids criteria')
        identifier(item['id'], requirement_ids)
        text(item['text'])
        need(isinstance(item['basis'], str) and item['basis'] in ('user-request', 'project-evidence', 'assumption'), 'unknown requirement basis')
        need(item['basis'] != 'assumption' or bool(value['assumptions']), 'record inferred assumptions explicitly')
        refs(item['evidence_ids'], evidence_ids)
        refs(item['criteria'], criteria)
        covered.update(item['criteria'])
    need(covered == criteria, 'every acceptance criterion needs a requirement')
    question_ids = set()
    for item in value['questions']:
        fields(item, 'id question options recommendation rationale evidence_ids answer answer_source resolved_by')
        identifier(item['id'], question_ids)
        for key in ('question', 'rationale', 'answer', 'answer_source'):
            text(item[key])
        refs(item['evidence_ids'], evidence_ids)
        need(isinstance(item['options'], list) and len(item['options']) in (0, 2, 3), 'offer two or three options, or a necessary free-text question')
        option_ids = set()
        for option in item['options']:
            fields(option, 'id label tradeoff')
            identifier(option['id'], option_ids)
            text(option['label'])
            text(option['tradeoff'])
        need(isinstance(item['recommendation'], str) and (item['recommendation'] in option_ids if option_ids else item['recommendation'] == ''), 'recommend an offered option')
        need(isinstance(item['resolved_by'], str) and item['resolved_by'] in ('user', 'pm', 'architect', 'advisor', 'orchestrator'), 'unknown decision owner')
    steps, planned_requirements, planned_checks = set(), set(), set()
    for item in value['plan']:
        fields(item, 'id action requirement_ids checks')
        identifier(item['id'], steps)
        text(item['action'])
        refs(item['requirement_ids'], requirement_ids)
        refs(item['checks'], checks)
        planned_requirements.update(item['requirement_ids'])
        planned_checks.update(item['checks'])
    need(planned_requirements == requirement_ids and planned_checks == checks, 'plan must cover all requirements and frozen checks')
    need(len(json.dumps(value, ensure_ascii=False).encode('utf-8')) <= 128 * 1024, 'brief exceeds 128 KiB; keep summaries and source pointers')
