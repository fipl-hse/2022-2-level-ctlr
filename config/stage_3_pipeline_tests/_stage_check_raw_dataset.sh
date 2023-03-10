set -e

echo -e '\n'
echo "Check raw dataset"

TARGET_SCORE=$(bash config/get_mark.sh lab_6_pipeline)

source venv/bin/activate

if [[ ${TARGET_SCORE} != 0 ]]; then
  mkdir -p tmp/articles
  if [[ ${TARGET_SCORE} != 4 ]]; then
    mv *_meta.json tmp/articles
  fi
  mv *_raw.txt tmp/articles
  python -m pytest -m "mark10 and stage_3_1_dataset_sanity_checks" --capture=no
else
  echo "Skip stage"
fi
