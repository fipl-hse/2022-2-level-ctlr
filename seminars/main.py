import random
from bs4 import BeautifulSoup
import re
import requests


def main():
    # response = requests.get('https://glasnaya.media/2023/03/13/nakazanie-rodinoj-aeroflot-vnov-okazalsya-v-centre-diskriminacionnogo-skandala/', headers={
    #     'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    # })
    response = requests.get('https://glasnaya.media/', headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    })
    # sleep_time = random.randrange(4, 10)
    # time.sleep(sleep_time)
    print(response.status_code)
    # file = open('Text_response.html', 'w', encoding='utf-8')
    # file.write(response.text)
    # file.close()

    main_bs = BeautifulSoup(response.text, 'lxml') # using lxml parser so the code is faster

    title_bs = main_bs.title
    # method to get tags that are matching:

    all_links_bs = main_bs.find_all('a') # a list of tags

    # print(title_bs.text)
    # print(title_bs.name)
    # print(title_bs.attrs)
    print(len(all_links_bs))

    all_links = []
    other_links = []
    for link_bs in all_links_bs:
        link = link_bs.get('href')
        if link is None:
            other_links.append(link_bs)
            print(link_bs)
            continue
        all_links.append(link_bs['href'])

    #print('all:', all_links)
    answers = []
    for elem in all_links:
        ans = re.findall(r'https://\w+.media/\d{4}/\d{2}/\d{2}/\S+[^/]/', elem)
        if ans and ans not in answers:
            answers.append(ans)
    print('!!! articles !!!', '\n',answers, sep='\n')

if __name__ == '__main__':
    main()
