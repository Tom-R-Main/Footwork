"""Post-boundary evidence for filmed pointer moves; never an OS-delivery receipt."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any


def uptime_raw_ns() -> int:
    """macOS uptime in nanoseconds, with the mach_absolute_time epoch (no process offset)."""
    return time.clock_gettime_ns(time.CLOCK_UPTIME_RAW)


def display_geometry() -> list[dict[str, Any]]:
    """Read each active display's actual backing scale, including non-main displays."""
    import AppKit
    import Quartz

    displays = []
    for screen in AppKit.NSScreen.screens():
        identifier = int(screen.deviceDescription()['NSScreenNumber'])
        bounds = Quartz.CGDisplayBounds(identifier)
        displays.append({'id': identifier, 'bounds': [bounds.origin.x, bounds.origin.y,
                                                    bounds.size.width, bounds.size.height],
                         'backing_scale': float(screen.backingScaleFactor())})
    return displays


class GestureTrace:
    """Accumulate small timestamp tuples during posts; encode/write only after playback."""

    def __init__(self, filmed: Any, kind: str, label: str, start: Any, target: Any,
                 plan: Any = None, *, completeness: str = 'complete') -> None:
        self.path = filmed.trace_path
        self.plan = plan
        self.posts: list[tuple[int, int, float, float, str]] = []
        self.errors: list[dict[str, Any]] = []
        started_ns = uptime_raw_ns()
        self.record: dict[str, Any] = {
            'schema': 'pointer_gesture/1', 'clock': 'CLOCK_UPTIME_RAW',
            'timestamp_unit': 'ns', 'kind': kind, 'label': label,
            'start': list(start), 'requested_target': list(target) if target is not None else None,
            't0_ns': started_ns, 'playback_started_ns': started_ns, 'planned_samples': [], 'posted_samples': [],
            'final_location': None, 'outcome': 'exception', 'completeness': completeness,
            'space': {'coordinates': 'global_screen_points', 'origin': 'top_left', 'unit': 'pt'},
            'window_origin': list(filmed.window[:2]), 'content_origin': list(filmed.content[:2]),
            'displays': [], 'backing_scale': None,
            'posted_basis': 'poster_call_entry; post_returned_ns bounds the call; not OS delivery',
        }
        try:
            self.record['displays'] = display_geometry()
            self.record['backing_scale'] = self.scale_at(target if target is not None else start)
            if self.record['backing_scale'] is None:
                self.record['geometry_complete'] = False
            else:
                self.record['geometry_complete'] = True
        except Exception as exc:  # noqa: BLE001 - metadata must not change pointer outcomes
            self.record['metadata_error'] = type(exc).__name__
            self.record['geometry_complete'] = False

    def scale_at(self, point: Any) -> float | None:
        for display in self.record['displays']:
            x, y, w, h = display['bounds']
            if x <= point[0] < x + w and y <= point[1] < y + h:
                return display['backing_scale']
        return None

    def started(self, scheduler_t0: float, clock: Any) -> None:
        before = uptime_raw_ns()
        scheduler_now = clock.now()
        after = uptime_raw_ns()
        self.record['t0_ns'] = (before + after) // 2 + round((scheduler_t0 - scheduler_now) * 1e9)
        self.record['clock_mapping_uncertainty_ns'] = after - before

    def post(self, event: str, x: float, y: float, call: Any) -> Any:
        began = uptime_raw_ns()
        try:
            result = call()
        except BaseException as exc:
            self.errors.append({'t_ns': began, 'x': x, 'y': y,
                                'event': event, 'error': type(exc).__name__})
            raise
        self.posts.append((began, uptime_raw_ns(), x, y, event))
        return result

    def poster(self, poster: Any) -> Any:
        trace = self
        if hasattr(poster, "record_posts"):
            poster.record_posts(self)
            self.record['posted_basis'] = 'CGEventPost call entry/return; not OS delivery'
            return poster

        class RecordingPoster:
            def __getattr__(self, key: str) -> Any:
                method = getattr(poster, key)
                if key not in ('move', 'drag', 'down', 'up'):
                    return method

                def post(x: float, y: float) -> Any:
                    return trace.post(key, x, y, lambda: method(x, y))
                return post
        return RecordingPoster()

    def measure_final(self, poster: Any) -> None:
        try:
            self.record['final_location'] = list(poster.location())
            self.record['final_measured_ns'] = uptime_raw_ns()
        except Exception as exc:  # noqa: BLE001 - preserve the original input outcome
            self.record['final_measurement_error'] = type(exc).__name__

    def finish(self, poster: Any, outcome: str, result: Any = None) -> dict[str, Any]:
        self.record['outcome'] = outcome
        if 'final_measured_ns' not in self.record and 'final_measurement_error' not in self.record:
            self.measure_final(poster)
        if self.plan is not None:
            self.record['planned_samples'] = [
                {'t_ns': self.record['t0_ns'] + round(s.t * 1e9), 'x': s.x, 'y': s.y}
                for s in self.plan.samples]
        self.record['posted_samples'] = None if self.record['completeness'] == 'unavailable_sdk_samples' else [
            {'t_ns': began, 'post_returned_ns': ended, 'x': x, 'y': y, 'event': event,
             'backing_scale': self.scale_at((x, y))}
            for began, ended, x, y, event in self.posts]
        if self.errors:
            self.record['post_errors'] = self.errors
            self.record['completeness'] = 'post_error_outcome_unknown'
        if result is not None:
            self.record.update(posted=result.posted_drags, max_gap_s=result.max_gap_s,
                               lateness_s=result.lateness_s, causes=result.causes)
        if self.path:
            try:
                with Path(self.path).open('a') as stream:
                    stream.write(json.dumps(self.record, separators=(',', ':')) + '\n')
            except OSError as exc:
                print(f'pointer recording failed: {type(exc).__name__}: {self.path}', file=sys.stderr)
        return self.record
