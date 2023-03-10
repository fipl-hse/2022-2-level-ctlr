"""
Checking whether PR author is admin or not
"""
import sys
from pathlib import Path
from typing import Optional

from tap import Tap

from config.collect_coverage.run_coverage import get_target_score
from config.stage_1_style_tests.pr_name_check import is_author_admin
from config.test_params import PROJECT_ROOT


class ArgumentParser(Tap):
    """
    Types for the argument parser
    """
    pr_name: Optional[str] = None
    pr_author: Optional[str] = None
    lab_path: Optional[Path] = None


def main() -> None:
    """
    Entrypoint for checking if PR has skip in name
    """
    args = ArgumentParser().parse_args()

    if (args.pr_name is not None) and ('[skip-lab]' in str(args.pr_name)):
        print('Skipping PR name checks due to label.')
        sys.exit(0)

    if args.pr_author and is_author_admin(args.pr_author):
        print('Skipping PR name checks due to author.')
        sys.exit(0)

    if args.lab_path:
        score_path = PROJECT_ROOT / args.lab_path
        score = get_target_score(lab_path=score_path)
        if score == 0:
            print('Skipping PR due to no mark.')
            sys.exit(0)

    print('No special reasons for skip!')
    sys.exit(1)


if __name__ == '__main__':
    main()
