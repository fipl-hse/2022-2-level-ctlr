# pylint: skip-file
import argparse
import re
import sys
from pathlib import Path
from re import Pattern


def convert_raw_pr_name(pr_name_raw: str) -> str:
    return pr_name_raw.replace('_', ' ')


def is_matching_name(pr_name: str, compiled_pattern: Pattern, example_name: str) -> bool:
    if not re.search(compiled_pattern, pr_name):
        print('Your Pull Request title does not confirm to the template.')
        print(example_name, end='\n\n')
        return False

    print('Your Pull Request name confirms to provided template.')
    return True


def load_pr_name_regex() -> Pattern:
    with (Path(__file__).parent / 'template_pr_name_regex.txt').open(encoding='utf-8') as f:
        lines = map(str.strip, f.readlines())
    return re.compile(next(lines))


def load_pr_name_example() -> str:
    with (Path(__file__).parent / 'template_pr_name_example.txt').open(encoding='utf-8') as f:
        lines = map(str.strip, f.readlines())
    return next(lines)


def is_author_admin(author_login: str) -> bool:
    admins_path = Path(__file__).parent.parent / 'admins.txt'
    with admins_path.open(encoding='utf-8') as f:
        admins_logins = tuple(map(str.strip, f.readlines()))

    return author_login in admins_logins


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks that PR name is done using the template')
    parser.add_argument('--pr-name', type=str, help='Current PR name')
    parser.add_argument('--pr-author', type=str, help='Current PR author')
    args: argparse.Namespace = parser.parse_args()

    if '[skip-name]' in args.pr_name:
        print("Skipping PR name checks.")
        sys.exit(0)

    if is_author_admin(args.pr_author):
        print('Skipping PR name checks due to author.')
        sys.exit(0)

    pr_name = convert_raw_pr_name(args.pr_name)
    compiled_pattern = load_pr_name_regex()
    example_name = load_pr_name_example()

    sys.exit(not is_matching_name(pr_name, compiled_pattern, example_name))
