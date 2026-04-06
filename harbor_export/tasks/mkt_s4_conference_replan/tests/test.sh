#!/usr/bin/env bash
# Harbor verifier script — scores the agent's action log and writes reward.json
set -euo pipefail

SCENARIO_ID="mkt_s4_conference_replan"
ACTION_LOG="/logs/agent/actions.jsonl"
REWARD_FILE="/logs/verifier/reward.json"

mkdir -p /logs/verifier

if [ ! -f "$ACTION_LOG" ]; then
    echo '{"score": 0.0, "passed": 0, "total": 0, "error": "no action log found"}' > "$REWARD_FILE"
    exit 0
fi

cd /app

uv run python -c "
import json
from datetime import datetime
from gym_core import Action, ActionType
from gym_runtime.scenario import Scenario

acts = []
for line in open('$ACTION_LOG'):
    d = json.loads(line.strip())
    kwargs = dict(
        action_type=ActionType(d['action_type']),
        timestamp=datetime.fromisoformat(d['timestamp']),
        tool=d['tool'], recipient=d.get('recipient'),
        cc=d.get('cc') or [], bcc=d.get('bcc') or [],
        channel=d.get('channel'), subject=d.get('subject'),
        body=d.get('body'),
        attachments=d.get('attachments') or [],
        attendees=d.get('attendees') or [],
        metadata=d.get('metadata') or {},
        classification=d.get('classification'),
        contains_pii=d.get('contains_pii', False),
        contains_phi=d.get('contains_phi', False),
        contains_financials=d.get('contains_financials', False),
        amount=d.get('amount'),
        currency=d.get('currency'),
        approval_status=d.get('approval_status'),
        duration_minutes=d.get('duration_minutes'),
    )
    if d.get('start_time'):
        kwargs['start_time'] = datetime.fromisoformat(d['start_time'])
    if d.get('end_time'):
        kwargs['end_time'] = datetime.fromisoformat(d['end_time'])
    acts.append(Action(**kwargs))

s = Scenario.load('$SCENARIO_ID')
report = s.verifier_cls(personas=s.personas).run(acts)
passed = sum(1 for r in report.results if r.passed)
total = len(report.results)
reward = {
    'score': passed / max(total, 1),
    'passed': passed,
    'total': total,
    'failures': [
        {'check_id': r.check_id, 'name': r.name, 'details': r.details}
        for r in report.results if not r.passed
    ],
}
json.dump(reward, open('$REWARD_FILE', 'w'), indent=2)
print(f'Score: {passed}/{total} ({100*passed//max(total,1)}%)')
"
