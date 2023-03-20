import random
import time

import requests
from requests import Timeout, HTTPError

if __name__ == '__main__':
    # 1. requests basics
    CORRECT_URL = 'https://pypi.org/project/requests/'
    INCORRECT_URL = f'{CORRECT_URL}garbagegarbage'

    response = requests.get(CORRECT_URL)
    if response:
        print(f'Response code is: {response.status_code}')

    if response.ok:
        print('Response is OK')

    try:
        response = requests.get(INCORRECT_URL)
        response.raise_for_status()
    except HTTPError as e:
        print(f'Error occurred: {e.response.status_code}')

    # 2. requests advanced
    # 2.1 handling timeouts, need to specify it for long responding servers
    try:
        response = requests.get(INCORRECT_URL, timeout=0.000001)
    except Timeout as e:
        print(f'In timeout: {e}')

    # 2.2 making pauses between requests to make them look more natural for a server
    response = requests.get(CORRECT_URL)

    sleep_period = 10
    print(f'Sleeping for {sleep_period}')
    time.sleep(sleep_period)

    response = requests.get(CORRECT_URL)

    sleep_period = random.randrange(3, 7)
    print(f'Sleeping for {sleep_period}')
    time.sleep(sleep_period)

    response = requests.get(CORRECT_URL)

    # 2.3 specifying browser headers to make a request look more natural for a server
    response = requests.get(CORRECT_URL)
    print(response.request.headers)
    print(response.headers)

    response = requests.get(CORRECT_URL, headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'
    })
    print(response.request.headers)
    print(response.headers)

    # 3. working with responses
    # 3.1 getting HTML page content as a plain Python string
    response = requests.get(CORRECT_URL)
    print(response.text)

    # 3.2 saving HTML page as a file
    response = requests.get(CORRECT_URL)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(response.text)

    # 3.3 saving binary files formats, such as images
    response = requests.get('https://pypi.org/static/images/logo-small.95de8436.svg')

    with open('logo.svg', 'wb') as f:
        f.write(response.content)
