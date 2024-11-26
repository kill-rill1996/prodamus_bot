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