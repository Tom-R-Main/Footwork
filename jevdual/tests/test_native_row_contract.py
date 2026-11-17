"""Public-CLI row identity feasibility, with separate supported positive controls.

No row promotion or dispatch implementation: the unchanged runtime must refuse
unnamed-row key inference. The fixture supplies both SDK and native ancestry.
"""
import pytest

from tests import test_session_scenarios as scenarios
from tests.test_session_scenarios import _native_identified_controls, _state

fw = scenarios.fw
world = scenarios.world


def row_world(world, monkeypatch, variant='complete', proof=None):
    identities = None if proof == 'dom' else [None, None]
    rows, backing, clicked = _native_identified_controls(world, monkeypatch, identities)
    table = {'element_index': 800, 'role': 'AXTable', 'label': 'Tasks', 'parent_index': 0}
    world.base['elements'].append(table)
    # A real, independent native hierarchy exists even if the SDK drops parents/tokens.
    document = {'role': 'AXWebArea', 'url': 'https://example.test/song/a', 'children': []}
    native_table = {'role': 'AXTable', 'parent': document, 'children': []}
    document['children'].append(native_table)
    for offset, popup in enumerate(rows):
        row_id, cell_id = 810 + offset * 10, 811 + offset * 10
        popup.update(label='Open menu', parent_index=cell_id)
        sdk_row = {'element_index': row_id, 'role': 'AXRow', 'label': f'Row {offset}' if proof == 'section' else '', 'parent_index': 800}
        world.base['elements'] += [sdk_row,
            {'element_index': cell_id, 'role': 'AXCell', 'label': '', 'parent_index': row_id},
            {'element_index': cell_id + 1, 'role': 'AXStaticText', 'label': f'TASK-{offset}', 'parent_index': cell_id}]
        native_row = {'role': 'AXRow', 'name': '', 'parent': native_table, 'children': []}
        native_table['children'].append(native_row)
        native_row['children'] += [{'role': 'AXCell', 'key_column': 'Task ID', 'value': f'TASK-{offset}', 'parent': native_row},
                                   {'role': 'AXPopUpButton', 'name': 'Open menu', 'parent': native_row, 'sdk_index': popup['element_index']}]
    if variant == 'flattened':
        world.base['elements'] = [r for r in world.base['elements'] if r.get('element_index') not in {800, 810, 811, 812, 820, 821, 822}]
        for row in rows: row['parent_index'] = 0
    if variant == 'tokenless':
        original = world.get_window_state
        async def observe(inp):
            snap = await original(inp)
            for row in snap['elements']:
                if row['element_index'] in (940, 941): row['element_token'] = None
            return snap
        monkeypatch.setattr(world, 'get_window_state', observe)
    # The initial helper's click spy records backing identity. Record the exact SDK
    # target too, because named sections legitimately do not require a DOM identity.
    original_click = world.click
    recipients = []
    async def click(inp):
        recipients.append(int(inp.position.element_token.split(':')[-1]))
        return await original_click(inp)
    monkeypatch.setattr(world, 'click', click)
    return document, rows, backing, clicked, recipients


@pytest.mark.parametrize('variant', ['complete', 'flattened', 'tokenless'])
def test_unnamed_row_key_is_not_existing_public_identity(world, fw, monkeypatch, variant):
    document, _rows, _backing, clicked, recipients = row_world(world, monkeypatch, variant)
    assert document['children'][0]['children'][0]['children'][0]['value'] == 'TASK-0'
    assert fw('start', 'Open TASK-0 row menu', '--app', 'Calculator')[0] == 0
    saved = _state(fw)
    offered = [c for c in saved['last_candidates'] if c['label'] == 'Open menu']
    if variant == 'tokenless':
        assert offered == []
    else:
        assert len(offered) == 1 and offered[0]['section'] is None
        assert offered[0]['id'] in saved['last_native_ambiguous']
    code, out, err = fw('do', 'click', 'section:TASK-0::combobox:Open menu')
    assert code != 0 and not clicked and not recipients, (out, err)


@pytest.mark.parametrize('proof,selector', [('section', 'section:Row 0::combobox:Open menu'), ('dom', '940')])
def test_existing_explicit_section_or_dom_identity_is_positive_control(world, fw, monkeypatch, proof, selector):
    _document, _rows, _backing, _clicked, recipients = row_world(world, monkeypatch, proof=proof)
    assert fw('start', 'Open selected row menu', '--app', 'Calculator')[0] == 0
    saved = [c for c in _state(fw)['last_candidates'] if c['label'] == 'Open menu']
    assert len(saved) == 2
    if proof == 'section': assert saved[0]['section'] == 'Row 0'
    else: assert saved[0]['native_dom_id'] == 'hero-options'
    code, out, err = fw('do', 'click', selector)
    assert code == 0 and recipients == [940], (out, err, recipients)
