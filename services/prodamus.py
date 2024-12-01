from prodamuspy import ProdamusPy
import requests
from settings import settings


def get_pay_link(tg_id: int) -> str:
    """Получение ссылки на оплату"""
    link_form = settings.pay_link

    data = {
        "order_id": tg_id,
        # "customer_phone": "79679185021",
        # "customer_email": "andreev.kirill2023@mail.ru",
        "subscription": settings.sub_number,
        # "subscription_date_start": "2024-11-12 23:00",

        "customer_extra": "Информация об оплачиваемой подписке",
        "do": "link",
        "sys": "",
    }

    response = requests.get(link_form, params=data)
    print(response)
    payment_link = response.content.decode()
    print(payment_link)
    return payment_link


def cancel_sub_by_user(phone: str) -> int:
    """Отмена подписки клиентом, ее невозможно будет уже включить только оформить повторно"""
    url = settings.pay_link + "rest/setActivity/"

    data_str = f"" \
           f"'subscription' => {settings.sub_number}," \
           f"\n'customer_phone' => {phone},\n" \
           f"'active_user' => 0"

    prodamus = ProdamusPy(settings.pay_token)
    body = prodamus.parse(data_str)
    signature = prodamus.sign(body)

    data_dict = {
        "subscription": settings.sub_number,
        "customer_phone": phone,
        "active_user": 0,
        "signature": signature
    }

    response = requests.get(url, params=data_dict)
    print(response)

    return response.status_code

