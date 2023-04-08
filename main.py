import requests
from bs4 import BeautifulSoup

def main():

    url = 'https://www.fontanka.ru/2023/04/06/72197210/'
    response = requests.get(url)
    print(response.status_code)

    main_bs = BeautifulSoup(response.text, 'lxml')

    """
    <h1 item
    """
    title_bs = main_bs.find_all('h1')
    print(title_bs[0].text, type(title_bs[0]))


if __name__ == '__main__':
    main()
