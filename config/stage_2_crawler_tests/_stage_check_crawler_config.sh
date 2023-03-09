set -x

source venv/bin/activate

python config/skip_check.py --pr_name "$1" --pr_author "$2" --lab_path "lab_5_scrapper"
if [ $? -eq 0 ]; then
  echo 'skip check due to special conditions...' && exit 0
fi

python -m pytest -m "mark10 and stage_2_1_crawler_config_check" --capture=no
