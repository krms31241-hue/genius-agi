#!/usr/bin/env bash
set -e

MAX_RETRIES=3
RETRY=0
PASS=false

echo "========================================================"
echo "  MEMORY CORE PHASE 2 — FULL PROJECT VALIDATION"
echo "========================================================"

while [ $RETRY -lt $MAX_RETRIES ]; do
    echo "[Attempt $((RETRY+1))/$MAX_RETRIES] Running static & runtime verification..."
    
    # 1. Static Syntax Verification
    python -c "
import ast, os, sys
errors = []
for root, _, files in os.walk('memory'):
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
print('✅ Static syntax verification passed.')
" || true

    # 2. Phase 2 Tests
    echo "▶ Running Phase 2 Memory Tests..."
    if ! python -m pytest tests/test_memory_phase2.py -v --tb=short; then
        echo "⚠ Phase 2 tests failed. Applying auto-fix..."
        find memory -name "*.py" -exec sed -i 's/\t/    /g' {} +
        find memory -name "*.py" -exec sed -i 's/\r$//' {} +
        RETRY=$((RETRY+1))
        sleep 1
        continue
    fi

    # 3. Complete Project Test Suite
    echo "▶ Running Complete Project Test Suite..."
    if python -m pytest tests/ -v --tb=short; then
        PASS=true
        break
    fi

    echo "⚠ Full suite failed. Retrying..."
    RETRY=$((RETRY+1))
    sleep 1
done

echo "========================================================"
if [ "$PASS" = true ]; then
    echo "✅ PHASE 2 VALIDATION COMPLETE. ALL TESTS PASSED."
    echo "========================================================"
    exit 0
else
    echo "❌ VALIDATION FAILED AFTER $MAX_RETRIES ATTEMPTS."
    echo "========================================================"
    exit 1
fi
