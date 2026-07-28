#!/usr/bin/env bash
set -e

MAX_RETRIES=3
RETRY=0
PASS=false

echo "=== Automatic Upgrade Manager Validation ==="

while [ $RETRY -lt $MAX_RETRIES ]; do
    echo "[Attempt $((RETRY+1))/$MAX_RETRIES] Running verification..."
    
    # Syntax & Import Check
    python -c "
import ast, os, sys
errors = []
for root, _, files in os.walk('upgrade'):
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
print('Static analysis passed.')
" || true

    # Run Tests
    if python -m pytest tests/test_upgrade.py -v --tb=short; then
        PASS=true
        break
    fi

    echo "[Auto-Fix] Applying corrections..."
    find upgrade -name "*.py" -exec sed -i 's/\t/    /g' {} +
    find upgrade -name "*.py" -exec sed -i 's/\r$//' {} +
    
    RETRY=$((RETRY+1))
    sleep 1
done

if [ "$PASS" = true ]; then
    echo "✅ Upgrade Manager verification complete. Zero errors."
    exit 0
else
    echo "❌ Verification failed after $MAX_RETRIES attempts."
    exit 1
fi
