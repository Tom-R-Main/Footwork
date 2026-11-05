"""A desktop hover lands where the element is, on every backing scale.

CUA's desktop ``move_cursor`` takes native ``get_desktop_state`` screenshot pixels and divides them by the
main display's backing scale. Footwork reads AX frames in points. On a Retina display (scale 2), a hover
that passes points lands at half the intended coordinates (notebook PM1).
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("cua_driver")

from jevdual.native import NativeBridge
from jevdual.posture import ExecutionPolicy

from tests.fixtures.native_world import World
from tests.test_posture import Activity

pytestmark = pytest.mark.usefixtures("mac_native_contract")

SEVEN = 5  # the recorded Calculator's "7": frame x439 y545 w48 h48, centre (463, 569) in points


def _hover(scale: float) -> World:
    world = World(scale=scale)
    policy = ExecutionPolicy("exclusive_desktop", activity=Activity())
    bridge = NativeBridge(world, 77, world.window_id, policy=policy)
    nm = asyncio.run(bridge.observe())
    object.__setattr__(nm.menu.candidate(SEVEN), "operations", ("click", "hover"))
    eff = asyncio.run(bridge.act(nm, "hover", SEVEN))
    assert eff.dispatched and eff.delivery == "desktop", eff
    return world


@pytest.mark.parametrize("scale", [1.0, 2.0])
def test_hover_lands_at_the_element_centre_in_points(scale):
    world = _hover(scale)
    assert world.pointer == pytest.approx((463.0, 569.0))
