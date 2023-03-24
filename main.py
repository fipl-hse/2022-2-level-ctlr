import requests

def main():
    response = requests.get('https://newstula.ru/cat_interview.html')
    print(response.status_code)



if __name__ == '__main__'
    main()