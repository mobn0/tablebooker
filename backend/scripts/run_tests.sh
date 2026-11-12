#!/usr/bin/env sh
# Runs the unit tests and the mutation tests, writes the reports to backend/reports/.
# Usage (from the repo root or backend/): sh backend/scripts/run_tests.sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports

echo "== Unit tests =="
python -m pytest -v --junitxml=reports/junit.xml

echo "== Mutation tests (app/services.py, app/scheduling.py) =="
rm -rf mutants
mutmut run --max-children 4 > /dev/null 2>&1 || true
mutmut results --all true > reports/mutation-report.txt 2>/dev/null

total=$(grep -c ': ' reports/mutation-report.txt || true)
killed=$(grep -c ': killed' reports/mutation-report.txt || true)
echo "Mutants killed: $killed / $total"
# Diff of every generated mutant, so the report shows what was changed
{ echo; echo "== Mutant diffs =="; } >> reports/mutation-report.txt
for id in $(cut -d: -f1 reports/mutation-report.txt | grep mutmut_); do
    mutmut show "$id" >> reports/mutation-report.txt 2>/dev/null || true
    echo >> reports/mutation-report.txt
done

if [ "$total" -eq 0 ] || [ "$killed" -ne "$total" ]; then
    echo "FAIL: not all mutants were killed (see reports/mutation-report.txt)"
    exit 1
fi
echo "OK: mutation score 100%"
