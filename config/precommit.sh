set -x

python -m pylint --exit-zero --rcfile config/stage_1_style_tests/.pylintrc seminars core_utils config

mypy seminars core_utils config

python -m flake8 --config ./config/stage_1_style_tests/.flake8 seminars core_utils config
