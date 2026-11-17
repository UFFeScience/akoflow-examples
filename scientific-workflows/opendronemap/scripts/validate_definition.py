import hashlib
import json
from pathlib import Path
import yaml
import run_stage

root = Path('/app')
workflow = yaml.safe_load((root / 'workflow.yaml').read_text())['spec']
contract = json.loads((root / 'data/input.json').read_text())
source = json.loads((root / 'data/source.json').read_text())
assert Path('/code/VERSION').read_text().strip() == '3.5.6'
assert len(source['files']) == 77
for item in source['files']:
    assert hashlib.sha256((root / 'data/images' / item['name']).read_bytes()).hexdigest() == item['sha256']
activities = {item['name']: item for item in workflow['activities']}
assert len(activities) == 9 and set(activities) == set(contract['stages'])
remaining, completed = set(activities), set()
while remaining:
    ready = {name for name in remaining if set(activities[name].get('dependsOn', [])) <= completed}
    assert ready, 'Workflow has a cycle or missing predecessor'
    completed |= ready
    remaining -= ready
for name, activity in activities.items():
    assert set(activity.get('dependsOn', [])) == set(contract['dependencies'][name])
    assert activity['command']['entrypoint'] == 'python3'
    assert activity['command']['arguments'][:3] == ['/app/scripts/run_stage.py', '--stage', name]
for prefix, parent in [('reconstruct', 'split'), ('process', 'align')]:
    for part in range(2):
        assert activities[f'{prefix}-{part}']['dependsOn'] == [parent]
for handoff in workflow['dataDependencies']:
    assert handoff['producerActivity'] in activities[handoff['consumerActivity']]['dependsOn']
assert callable(run_stage.OSFMContext.align_reconstructions)
assert callable(run_stage.ODMMergeStage.process)
print('Validated pinned native ODM runtime, 77 real photograph hashes and nine-activity parallel split/merge contract; scientific completion requires run.sh.')
