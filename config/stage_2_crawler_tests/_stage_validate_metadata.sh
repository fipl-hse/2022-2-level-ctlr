set -x

source venv/bin/activate

export PYTHONPATH=$(pwd):$PYTHONPATH
python config/skip_check.py --pr_name "$1" --pr_author "$2" --lab_path "lab_5_scrapper"
if [ $? -eq 0 ]; then
  echo 'skip check due to special conditions...' && exit 0
fi

TARGET_SCORE=$(bash config/get_mark.sh lab_5_scrapper)

ls
mkdir -p tmp/articles
mv *_raw.txt tmp/articles
if [[ ${TARGET_SCORE} != 4 ]]; then
  mv *_meta.json tmp/articles
fi
bash config/stage_2_crawler_tests/s2_5_check_raw_data.sh
