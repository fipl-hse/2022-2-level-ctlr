set -x

source venv/bin/activate

export PYTHONPATH=$(pwd):$PYTHONPATH
python config/skip_check.py --pr_name "$1" --pr_author "$2" --lab_path "lab_5_scrapper"
if [ $? -eq 0 ]; then
  echo 'skip check due to special conditions...' && exit 0
fi

TARGET_SCORE=$(bash config/get_mark.sh lab_5_scrapper)
python -m pytest -m "mark${TARGET_SCORE} and stage_2_2_crawler_check" --capture=no

ret=$?
if [ "$ret" = 5 ]; then
  echo "No tests collected.  Exiting with 0 (instead of 5)."
  exit 0
fi

apt install curl
curl --version
curl -i -H "Accept: application/json" -H "Content-Type: application/json" -X GET https://livennov.ru/news/ -v

echo "!!!!now with python"
python lab_5_scrapper/sample.py


echo "Pytest results (should be 0): $ret"

exit "$ret"
