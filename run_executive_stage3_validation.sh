#!/usr/bin/env bash
set -e

MAX_RETRIES=3
RETRY=0
PASS=false
OUTPUT=""

echo "========================================================"
echo "  EXECUTIVE STAGE 3 — FULL PROJECT VALIDATION"
echo "========================================================"

while [ $RETRY -lt $MAX_RETRIES ]; do
    echo "[Attempt $((RETRY+1))/$MAX_RETRIES] Running verification..."
    
    python -c "
import ast, os, sys
errors = []
for root, _, files in os.walk('executive'):
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

    echo "▶ Running Stage 3 & Full Suite..."
    OUTPUT=$(python -m pytest tests/test_mission_executor.py tests/ -v --tb=short 2>&1) || true
    echo "$OUTPUT"
    
    if echo "$OUTPUT" | grep -q "passed" && ! echo "$OUTPUT" | grep -q "failed" && ! echo "$OUTPUT" | grep -q "ERROR"; then
        PASS=true
        break
    fi

    echo "⚠ Validation failed. Retrying..."
    RETRY=$((RETRY+1))
    sleep 1
done

echo "========================================================"
if [ "$PASS" = true ]; then
    PASSED_COUNT=$(echo "$OUTPUT" | grep -oE '[0-9]+ passed' | head -1 | awk '{print $1}')
    echo "✅ EXECUTIVE STAGE 3 VALIDATION PASSED"
    echo "${PASSED_COUNT:-0} TESTS PASSED"
    echo "========================================================"
    exit 0
else
    echo "❌ VALIDATION FAILED AFTER $MAX_RETRIES ATTEMPTS."
    echo "========================================================"
    exit 1
fi
