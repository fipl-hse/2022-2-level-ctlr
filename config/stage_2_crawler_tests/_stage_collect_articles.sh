set -ex

echo -e '\n'
echo 'Collect articles...'

TARGET_SCORE=$(bash config/get_mark.sh lab_5_scrapper)

source venv/bin/activate

IS_ADMIN=$(python config/is_admin.py --pr_name "$1")
if [ "$REPOSITORY_TYPE" == "public" ] && [ "$IS_ADMIN" == 'YES' ] ; then
  echo '[skip-lab] option was enabled, skipping check...'
  exit 0
fi

if [[ ${TARGET_SCORE} != 0 ]]; then
  bash config/stage_2_crawler_tests/s2_4_collect_articles_from_internet.sh
  ls -la tmp/articles
else
  echo "Skipping stage"
fi
