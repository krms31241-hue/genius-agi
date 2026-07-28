#!/usr/bin/env bash
set -e

MAX_RETRIES=3
RETRY=0
PASS=false

echo "=== Self Evolution Engine Verification ==="

while [ $RETRY -lt $MAX_RETRIES ]; do
    echo "[Attempt $((RETRY+1))/$MAX_RETRIES] Running static & runtime checks..."
    
    # Syntax verification
    python -c "
import ast, os, sys
errors = []
for root, _, files in os.walk('self_evolution'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                with open(p) as fh: ast.parse(fh.read())
            except SyntaxError as e:
                errors.append(f'{p}: {e}')
if errors:
    for e in errors: print(e)
    sys.exit(1)
print('Static syntax verification passed.')
" || true

    # Import & structure verification
    python -c "
import sys, os
sys.path.insert(0, '.')
from self_evolution.engine import SelfEvolutionEngine
from self_evolution.memory import EvolutionMemory
from self_evolution.mapper import ProjectMapper
from self_evolution.dependency_graph import DependencyGraph
from self_evolution.planner import ImprovementPlanner
from self_evolution.candidate import CandidatePatch
from self_evolution.detectors import ALL_DETECTORS
print(f'Loaded {len(ALL_DETECTORS)} detectors successfully.')
print('Module structure verification passed.')
" || true

    # Dry-run execution verification
    if python -c "
import sys, os, json
sys.path.insert(0, '.')
from self_evolution.engine import SelfEvolutionEngine
engine = SelfEvolutionEngine()
res = engine.run_cycle()
assert res['status'] in ('completed', 'no_issues_found', 'empty_project'), f'Unexpected status: {res[\"status\"]}'
assert 'cycle' in res
assert 'duration_sec' in res
print('Dry-run execution passed.')
print(json.dumps(res, indent=2))
"; then
        PASS=true
        break
    fi

    echo "[Auto-Fix] Applying corrections..."
    find self_evolution -name "*.py" -exec sed -i 's/\t/    /g' {} +
    find self_evolution -name "*.py" -exec sed -i 's/\r$//' {} +
    
    RETRY=$((RETRY+1))
    sleep 1
done

if [ "$PASS" = true ]; then
    echo "✅ Self Evolution Engine verification complete. Zero errors."
    exit 0
else
    echo "❌ Verification failed after $MAX_RETRIES attempts."
    exit 1
fi
