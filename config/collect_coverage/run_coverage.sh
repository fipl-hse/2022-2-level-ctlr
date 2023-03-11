set -x

source venv/bin/activate

python config/collect_coverage/coverage_analyzer.py
