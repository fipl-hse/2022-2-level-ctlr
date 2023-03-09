set -ex

echo -e '\n'
echo "Parser checks"

TARGET_SCORE=$(bash config/get_mark.sh lab_5_scrapper)

IS_ADMIN=$(python config/is_admin.py --pr_name "$1")
if [ "$REPOSITORY_TYPE" == "public" ] && [ "$IS_ADMIN" == 'YES' ] ; then
  echo '[skip-lab] option was enabled, skipping check...'
  exit 0
fi

if [[ ${TARGET_SCORE} != 0 ]]; then
  bash config/stage_2_crawler_tests/s2_3_check_parser.sh
else
  echo "Skipping stage"
fi
