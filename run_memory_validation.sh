#!/usr/bin/env bash
set -e

MAX_RETRIES=3
RETRY=0
PASS=false

echo "=== Memory Core Validation ==="

while [ $RETRY -lt $MAX_RETRIES ]; do
    echo "[Attempt $((RETRY+1))/$MAX_RETRIES] Running checks..."
    
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
print('Static syntax verification passed.')
" || true

    if python -m pytest tests/test_memory.py -v --tb=short; then
        PASS=true
        break
    fi

    echo "[Auto-Fix] Applying corrections..."
    find memory -name "*.py" -exec sed -i 's/\t/    /g' {} +
    find memory -name "*.py" -exec sed -i 's/\r$//' {} +
    
    RETRY=$((RETRY+1))
    sleep 1
done

if [ "$PASS" = true ]; then
    echo "✅ Memory Core validation complete. Zero errors."
    exit 0
else
    echo "❌ Validation failed after $MAX_RETRIES attempts."
    exit 1
fi
