set -ex

echo -e '\n'
echo "Validate raw data"

TARGET_SCORE=$(bash config/get_mark.sh lab_5_scrapper)

source venv/bin/activate

IS_ADMIN=$(python config/is_admin.py --pr_name "$1")
if [ "$REPOSITORY_TYPE" == "public" ] && [ "$IS_ADMIN" == 'YES' ] ; then
  echo '[skip-lab] option was enabled, skipping check...'
  exit 0
fi

if [[ ${TARGET_SCORE} != 0 ]]; then
  ls
  mkdir -p tmp/articles
  mv *_raw.txt tmp/articles
  if [[ ${TARGET_SCORE} != 4 ]]; then
    mv *_meta.json tmp/articles
  fi
  bash config/stage_2_crawler_tests/s2_5_check_raw_data.sh
else
  echo "Skipping stage"
fi
