set -x

source venv/bin/activate

export PYTHONPATH=$(pwd):$PYTHONPATH
python config/skip_check.py --pr_name "$1" --pr_author "$2" --lab_path "lab_5_scrapper"
if [ $? -eq 0 ]; then
  echo 'skip check due to special conditions...' && exit 0
fi

bash config/stage_2_crawler_tests/s2_3_check_parser.sh
