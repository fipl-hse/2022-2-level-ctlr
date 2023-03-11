set -x

source venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH

python config/collect_coverage/coverage_analyzer.py
