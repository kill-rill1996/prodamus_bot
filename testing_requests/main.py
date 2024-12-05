import requests


def main():
    link_form = "https://sheva-nutrition.payform.ru/"
    print("TESTING REQ")

    data = {
        "order_id": 714371204,
        "subscription": 2093463,
        "customer_extra": "Информация об оплачиваемой подписке",
        "do": "link",
        "sys": ""
    }

    response = requests.get(link_form, params=data)
    print(response)
    payment_link = response.content.decode()
    print(payment_link)


if __name__ == '__main__':
    main()