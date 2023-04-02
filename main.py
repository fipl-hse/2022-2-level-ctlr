import requests

def main():
    response = requests.get('https://www.kommersant.ru/regions/52')

    print(response.status_code)


if __name__ == '__main__':
    main()
