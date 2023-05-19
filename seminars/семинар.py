# import requests
# from bs4 import BeautifulSoup
#
#
# def main():
#     response = requests.get('https://xn--80ady2a0c.xn--p1ai/calendar/2023/01/',
#                             headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
#                                                    '(KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'})
#
#     with open('article_tanya.html', 'w+', encoding='utf-8') as file:
#         file.write(response.text)
#
#     main_bs = BeautifulSoup(response.text, 'lxml')
#     # title_bs = main_bs.find_all('h1')[0]
#     # print(title_bs.text)
#
#     body_bs = main_bs.find_all('div', {'class': "calendar__search-result"})[0].find_all('a')
#     # body_bs = main_bs.find_all("a", {"class": "news-main--line-item"})
#     for p in body_bs:
#         url = p.get('href')
#         print(url)
#     # print(body_bs)
#     # print(type(body_bs))
#
#
# if __name__ == '__main__':
#     main()
