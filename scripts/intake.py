"""Validate a frozen user-intent record; this record never grants host permissions."""


def validate(value):
    fields = {'version', 'user_request_ref', 'authorized_actions', 'delegated_decisions',
              'known_inputs', 'assumptions', 'open_questions', 'escalation', 'native_approval'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('Intake requires the documented fields only')
    if type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Unsupported intake version')
    if value['escalation'] != 'block-affected-work' or value['native_approval'] != 'required-where-applicable':
        raise ValueError('Intake cannot waive host approval or authorize a bypass')

    def text(item):
        if not isinstance(item, str) or not item.strip() or len(item) > 2000:
            raise ValueError('Intake values need nonempty bounded text')

    text(value['user_request_ref'])
    for name in ('authorized_actions', 'delegated_decisions', 'known_inputs', 'assumptions', 'open_questions'):
        if not isinstance(value[name], list) or len(value[name]) > 30:
            raise ValueError('Intake lists must contain at most 30 entries')
    if value['open_questions']:
        raise ValueError('Resolve required intake questions before freezing the task')
    for name, keys in (('authorized_actions', {'action', 'scope', 'evidence'}),
                       ('delegated_decisions', {'topic', 'owner', 'limits'}),
                       ('known_inputs', {'name', 'value', 'source'})):
        for item in value[name]:
            if not isinstance(item, dict) or set(item) != keys:
                raise ValueError('Invalid intake ' + name + ' entry')
            for field in item.values():
                text(field)
            if name == 'delegated_decisions' and item['owner'] not in ('pm', 'architect', 'advisor', 'orchestrator'):
                raise ValueError('Unknown intake decision owner')
    for assumption in value['assumptions']:
        text(assumption)
