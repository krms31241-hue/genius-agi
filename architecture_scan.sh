#!/data/data/com.termux/files/usr/bin/bash

cd ~/genius-agi || exit 1

echo "======================================================"
echo "GENIUS-AGI ARCHITECTURE SCAN"
echo "======================================================"

echo
echo "===== PROJECT ====="
pwd

echo
echo "===== GIT ====="
git rev-parse --show-toplevel
git branch --show-current
git log --oneline -5

echo
echo "===== ROOT ====="
ls

echo
echo "===== TOP DIRECTORIES ====="
find . -maxdepth 2 -type d | sort

echo
echo "===== PYTHON FILES ====="
find . -name "*.py" | sort

echo
echo "===== TEST FILES ====="
find tests -name "*.py" | sort

echo
echo "===== VALIDATION SCRIPTS ====="
find . -maxdepth 1 -name "run_*"

echo
echo "===== TOOLS ====="
find tools -maxdepth 2 -type f

echo
echo "===== EXECUTIVE ====="
find executive -maxdepth 3 -type f

echo
echo "===== MEMORY ====="
find memory -maxdepth 3 -type f

echo
echo "===== DECISION ====="
find decision -maxdepth 3 -type f

echo
echo "===== GOVERNANCE ====="
find governance -maxdepth 3 -type f

echo
echo "===== LEARNING ====="
find learning -maxdepth 3 -type f

echo
echo "===== LAB ====="
find lab -maxdepth 3 -type f

echo
echo "===== PLANNER ====="
find planner -maxdepth 3 -type f

echo
echo "===== SIMULATION ====="
find simulation -maxdepth 3 -type f

echo
echo "===== SELF EVOLUTION ====="
find self_evolution -maxdepth 3 -type f

echo
echo "===== UPGRADE ====="
find upgrade -maxdepth 3 -type f

echo
echo "===== IMPORT GRAPH ====="
grep -R "^import " .
grep -R "^from " .

echo
echo "===== PYTEST COUNT ====="
find tests -name "test_*.py" | wc -l

echo
echo "===== GIT STATUS ====="
git status

echo
echo "======================================================"
echo "SCAN COMPLETE"
echo "======================================================"

