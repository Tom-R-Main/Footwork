"""Policy conformance uses a labelled fake CLI; it is not live model evidence."""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import codex_policy as policy
import operator_runtime


class PolicyTests(unittest.TestCase):
    def test_closed_action_schema_finite_targets_and_no_success_flag(self):
        valid = {"action": "move", "target_x": .01, "target_y": 0, "intent": "Push into the task region."}
        self.assertEqual(policy.validate_action(valid), valid)
        for changed in ({**valid, "target_x": True}, {**valid, "target_x": float("nan")},
                        {**valid, "target_x": .5}, {**valid, "success": True},
                        {**valid, "action": "measure"}, {**valid, "intent": ""}):
            with self.subTest(changed=changed), self.assertRaises((policy.PolicyUnavailable, ValueError)):
                policy.validate_action(changed)

    def test_usage_optional_and_any_tool_event_refuses(self):
        self.assertIsNone(policy.usage_from_events(b'{}\nnull\n'))
        usage = {"input_tokens": 20, "output_tokens": 10, "cached_input_tokens": 2}
        self.assertEqual(policy.usage_from_events(json.dumps({"type": "turn.completed", "usage": usage}).encode()), usage)
        for kind in ("command_execution", "file_change", "mcp_tool_call", "web_search", "tool_call", "plan", "image_view"):
            with self.subTest(kind=kind), self.assertRaises(policy.PolicyUnavailable):
                policy.usage_from_events(json.dumps({"type": "item.completed", "item": {"type": kind}}).encode())

    def test_fake_cli_bound_image_schema_tool_isolation_and_reservation(self):
        with tempfile.TemporaryDirectory(prefix="policy-test-", dir=policy.protocol.OUTPUT) as temp:
            root = Path(temp)
            operator_runtime.initialize(root / "operator")
            target = policy.agent_bench.AgentBench(root / "operator/agent")
            challenge = target.observe()
            fake = root / "fake-cli"
            fake.write_text("#!" + sys.executable + "\n" + '''import json,sys
from pathlib import Path
args=sys.argv[1:]
assert '--ignore-user-config' in args and '--ephemeral' in args
assert args[args.index('--sandbox')+1]=='read-only'
assert 'shell_tool' in args and 'tools.view_image=false' in args
assert 'web_search="disabled"' in args
png=Path(args[args.index('--image')+1]).read_bytes()
assert png.startswith(b'\\x89PNG')
prompt=sys.stdin.read()
assert 'block_center_xy' not in prompt and 'block_xyz' not in prompt
out=Path(args[args.index('--output-last-message')+1])
out.write_text(json.dumps({'action':'stop','target_x':None,'target_y':None,'intent':'Labelled fake policy.'}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':20,'output_tokens':10}}))
''')
            fake.chmod(0o700)
            call = root / "call"
            call.mkdir(mode=0o700)
            (call / "reservation.json").write_text("{}")
            with patch.object(policy, "preflight", return_value={"available": True, "cli_version": policy.EXPECTED_CLI}), patch.object(policy.shutil, "which", return_value=str(fake)):
                action, metadata = policy.decide(challenge, [{"block_center_xy": [1, 2], "block_xyz": [3, 4, 5]}], call, threading.Event())
                self.assertEqual(action["action"], "stop")
                self.assertTrue(metadata["process_exit_observed"])
                self.assertEqual(metadata["usage"]["input_tokens"], 20)
                with self.assertRaises(policy.PolicyUnavailable):
                    policy.decide(challenge, [], call, threading.Event())


if __name__ == "__main__":
    unittest.main()
