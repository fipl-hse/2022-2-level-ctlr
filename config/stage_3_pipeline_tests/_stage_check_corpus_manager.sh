set -ex

echo -e '\n'
echo "Check corpus manager creates instance appropriately"

TARGET_SCORE=$(bash config/get_mark.sh lab_6_pipeline)

if [[ ${TARGET_SCORE} != 0 ]]; then
  mkdir -p tmp/articles
  if [[ ${TARGET_SCORE} != 4 ]]; then
    mv *_meta.json tmp/articles
  fi
  mv *_raw.txt tmp/articles
  bash config/stage_3_pipeline_tests/s3_2_corpus_manager.sh
  ls -la tmp/articles
else
  echo "Skip stage"
fi
