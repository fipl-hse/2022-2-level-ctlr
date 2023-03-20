from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, urlunparse


def main():
    CORRECT_URL = 'https://www.nn.ru/text/economics/2022/03/10/70497161/'
    response = requests.get(CORRECT_URL)

    print(response.text)

    # 1. Creating instance of soup
    # install 'lxml' first or remove it from arguments below
    soup = BeautifulSoup(response.text, 'lxml')

    # 2. Getting tags by dot notation
    print(soup.title)
    print(type(soup.title))
    print(type(soup.title.text))

    # 3. Finding tags by their name
    all_spans = soup.find_all('span')
    print(f'Number of spans: {len(all_spans)}')

    # 4. Finding elements by their class
    header = soup.find_all(class_='_3Esly')
    if header:
        print(f'Found a header: {header}')
    else:
        print('Header not found')

    # 5. Finding elements by their id
    header = soup.find_all(id='record-header')
    if header:
        print(f'Found a header by ID: {header}')
    else:
        print('Header not found')

    # 6. You can mix them all if you need
    rating = soup.find_all('section', class_='_12gEL _2XsA2')
    if rating:
        print(f'Found a rating string: {rating}')
        print(rating[0].p.text)

    # 7. Find by css selector
    tags = soup.select('#app > div.global-wrapper > div.app-content > div > div > '
                       'div.inner-columns-wrapper > div.central-right-wrapper > '
                       'div.central-column-container > div.ye0Ux.mobile.tablet.laptop.desktop > '
                       'div._2SrRn > div > div._2TvYC')
    if tags:
        for link in tags[0].find_all('a'):
            print(link['title'])

    # 8. Find by custom attribute
    all_body = soup.find_all('div', itemprop='articleBody')

    texts = []
    if all_body:
        all_divs = all_body[0].find_all('div')
        texts = []
        for d in all_divs:
            texts.append(d.text)

    print(' '.join(texts))

    # 9. Find any link by tag and get its attributes
    all_links = soup.find_all('a')
    for link in all_links:
        try:
            address = link['href']
        except KeyError:
            continue
        parsed_address = urlparse(address)
        print(f'Parsing the URL: {address}. Protocol: {parsed_address.scheme}. Netloc: {parsed_address.netloc}.')
        print(f'\tPath: {parsed_address.path}. Params: {parsed_address.params}.')

        if not parsed_address.netloc:
            print(f'This is a relative path. Let us construct the full path.')
            full_url = urlunparse((
                urlparse(CORRECT_URL).scheme,
                urlparse(CORRECT_URL).netloc,
                parsed_address.path,
                None,
                None,
                None
            ))
            print(f'And it is: {full_url}')

    print('Found by custom attribute')


if __name__ == '__main__':
    main()
