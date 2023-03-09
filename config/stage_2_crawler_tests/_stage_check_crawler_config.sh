set -ex

echo -e '\n'
echo 'Running crawler config check...'

TARGET_SCORE=$(bash config/get_mark.sh lab_5_scrapper)
echo $TARGET_SCORE

source venv/bin/activate

IS_ADMIN=$(python config/is_admin.py --pr_name "$1")
if [ "$REPOSITORY_TYPE" == "public" ] && [ "$IS_ADMIN" == 'YES' ] ; then
  echo '[skip-lab] option was enabled, skipping check...'
  exit 0
fi

if [[ ${TARGET_SCORE} != 0 ]]; then
  python -m pytest -m "mark10 and stage_2_1_crawler_config_check" --capture=no
else
  echo "Skipping stage"
fi
