#!/usr/bin/env bash
set -e

MAX_RETRIES=3
RETRY=0
PASS=false

echo "=== Safe Autonomous Code Laboratory Validation ==="

while [ $RETRY -lt $MAX_RETRIES ]; do
    echo "[Attempt $((RETRY+1))/$MAX_RETRIES] Running tests..."
    if python -m pytest tests/test_lab.py -v --tb=short; then
        PASS=true
        break
    fi

    echo "[Auto-Fix] Applying corrective measures..."
    # Fix common issues automatically
    find lab -name "*.py" -exec sed -i 's/\t/    /g' {} +
    python -c "
import ast, os, sys
for root, _, files in os.walk('lab'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                with open(p) as fh: code = fh.read()
                ast.parse(code)
            except SyntaxError as e:
                print(f'Syntax issue in {p}: {e}')
                sys.exit(1)
print('Static syntax check passed.')
" || true

    RETRY=$((RETRY+1))
    sleep 1
done

if [ "$PASS" = true ]; then
    echo "✅ All laboratory validations passed."
    exit 0
else
    echo "❌ Validation failed after $MAX_RETRIES attempts."
    exit 1
fi
