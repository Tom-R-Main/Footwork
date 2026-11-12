"""Only a complete bounded direct parent chain can qualify an opaque native control."""

import sys
from types import SimpleNamespace

import pytest
from jevdual import ax


def _scope(monkeypatch, count):
    window = {'AXRole': 'AXWindow', '_pid': 77}
    page = {'AXRole': 'AXWebArea', 'AXURL': 'https://example.test/editor/a',
            'AXParent': window, '_pid': 77}
    parent = page
    for _ in range(count - 3):
        parent = {'AXRole': 'AXGroup', 'AXParent': parent, '_pid': 77}
    control = {'AXRole': 'AXPopUpButton', 'AXTitle': '', 'AXDescription': '',
               'AXDOMIdentifier': 'literal-id', 'AXParent': parent, '_pid': 77}
    reads = []

    def owner(node, _):
        reads.append(node)
        return node.get('_error', 0), node.get('_pid')

    monkeypatch.setattr(ax, '_attr', lambda node, name: node.get(name))
    monkeypatch.setattr(ax, 'same_element', lambda left, right: left is right)
    monkeypatch.setitem(sys.modules, 'ApplicationServices', SimpleNamespace(AXUIElementGetPid=owner))
    return control, page, window, reads


@pytest.mark.parametrize('count', [3, 32, 33, 34, 64])
@pytest.mark.parametrize('role', ['AXWindow', 'AXSheet'])
def test_complete_exact_scope_includes_the_64th_node(monkeypatch, count, role):
    control, page, window, reads = _scope(monkeypatch, count)
    window['AXRole'] = role
    proof = ax.control_backing(control, pid=77, window=window, role='AXPopUpButton')
    assert proof == {'dom_id': 'literal-id', 'document_url': 'https://example.test/editor/a',
                     'web_area': page, 'unnamed': True}
    assert len(reads) == count


@pytest.mark.parametrize('count', [65, 66, 129])
def test_scope_beyond_64_nodes_is_not_truncated_into_authority(monkeypatch, count):
    control, _, window, reads = _scope(monkeypatch, count)
    assert ax.control_backing(control, pid=77, window=window, role='AXPopUpButton') is None
    assert len(reads) == 64


@pytest.mark.parametrize('failure', ['foreign_owner', 'owner_error', 'unreadable_role', 'missing_parent',
                                   'bad_closest_url', 'other_window', 'application', 'no_webarea'])
def test_deep_scope_still_requires_every_owner_role_parent_and_closest_document(monkeypatch, failure):
    control, page, window, reads = _scope(monkeypatch, 34)
    parent = control['AXParent']
    if failure == 'foreign_owner': parent['_pid'] = 88
    elif failure == 'owner_error': parent['_error'] = -25200
    elif failure == 'unreadable_role': parent['AXRole'] = None
    elif failure == 'missing_parent': parent['AXParent'] = None
    elif failure == 'bad_closest_url':
        page['AXURL'] = '/relative'
        page['AXParent'] = {'AXRole': 'AXWebArea', 'AXURL': 'https://example.test/outer',
                            'AXParent': window, '_pid': 77}
    elif failure == 'other_window': page['AXParent'] = {'AXRole': 'AXWindow', '_pid': 77}
    elif failure == 'application': parent['AXRole'] = 'AXApplication'
    elif failure == 'no_webarea': page['AXRole'] = 'AXGroup'
    assert ax.control_backing(control, pid=77, window=window, role='AXPopUpButton') is None
    assert len(reads) <= 64


@pytest.mark.parametrize('alias', [False, True])
def test_native_equal_parent_cycles_stop_before_revisiting_a_node(monkeypatch, alias):
    control, _, window, reads = _scope(monkeypatch, 34)
    parent = control['AXParent']
    if alias:
        parent['_native'] = 123
        parent['AXParent'] = {'AXRole': 'AXGroup', '_pid': 77, '_native': 123}
        monkeypatch.setattr(ax, 'same_element', lambda left, right:
                            left.get('_native', id(left)) == right.get('_native', id(right)))
    else:
        parent['AXParent'] = parent
    assert ax.control_backing(control, pid=77, window=window, role='AXPopUpButton') is None
    assert len(reads) == 2
