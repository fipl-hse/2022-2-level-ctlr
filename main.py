import requests
from bs4 import BeautifulSoup
def main():
    response = requests.get('https://piter.tv/news/',
                            headers={
                                'user agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64);'
                                                   'AppleWebKit/537.36 (KHTML, like Gecko)'
                                                   'Chrome/108.0.0.0 YaBrowser/23.1.5.708 Yowser/2.5 Safari/537.36'
                                     }
                            )
    print(response.status_code)
    print(response.text)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(response.text)

    main_bs = BeautifulSoup(response.text, 'lxml')

    all_links_bs = main_bs.find_all('a')
    print(len(all_links_bs))

    all_links = []
    for link_bs in all_links_bs:
        href = link_bs.get('href')
        if href is None:
            print('href')
            continue
        elif href.startswith('https://piter.tv/event/'):
            all_links.append(href)
            print(href)
    print(all_links)


    url = 'https://piter.tv/event/pogoda_spb_7_aprelya_0/'
    response = requests.get(url)
    print(response.status_code)
    main_bs = BeautifulSoup(response.text, 'lxml')

    """
    <h1 class="article__title">В Петербурге 7 апреля будет солнечно и тепло</h1>
    """
    title_bs = main_bs.find_all('h1', {'class': 'article__title'})
    print(title_bs)#, type(title_bs))
    #span_bs = title_bs.find('span')
    #print(span_bs.text)

    url = "https://livennov.ru/news/2023-04-12-sinoptiki-predupredili-nizhegorodtsev-o-zamorozkakh-pered-paskhoy/"


if __name__ == '__main__':
    main()