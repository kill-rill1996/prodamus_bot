import hashlib
import json
import hmac
from collections.abc import MutableMapping

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
        # "subscription": settings.sub_number,
        # "subscription_date_start": "2024-11-12 23:00",

        "products[0][name]": "Подписка на 1 мес.",
        "products[0][price]": 50,
        "products[0][quantity]": 1,

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

    prodamus = ProdamusPy(settings.pay_token)

    data = {"subscription": settings.sub_number,
            "customer_phone": "+79679195042",
            "active_user": 0}

    signature_1 = prodamus.sign(data)
    signature_2 = sign(data, settings.pay_token)

    print(signature_1)
    print(signature_2)
    data["signature"] = signature_2

    post_response = requests.post(url, data=data)
    print(post_response.url)
    print(post_response.status_code)
    print(post_response.content)

    # get_response = requests.get(url, json=data)
    # print(get_response.status_code)
    # print(get_response.content)

    return post_response.status_code


def sign(data, secret_key):
    import hashlib
    import hmac
    import json

    # переводим все значения data в string c помощью кастомной функции deep_int_to_string (см ниже)
    deep_int_to_string(data)

    # переводим data в JSON, с сортировкой ключей в алфавитном порядке, без пробелом и экранируем бэкслеши
    data_json = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).replace("/", "\\/")

    # создаем подпись с помощью библиотеки hmac и возвращаем ее
    return hmac.new(secret_key.encode('utf8'), data_json.encode('utf8'), hashlib.sha256).hexdigest()


def deep_int_to_string(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, MutableMapping):
            deep_int_to_string(value)
        elif isinstance(value, list) or isinstance(value, tuple):
            for k, v in enumerate(value):
                deep_int_to_string({str(k): v})
        else:
            dictionary[key] = str(value)


def http_build_query(dictionary, parent_key=False):
    items = []
    for key, value in dictionary.items():
        new_key = str(parent_key) + '[' + key + ']' if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(http_build_query(value, new_key).items())
        elif isinstance(value, list) or isinstance(value, tuple):
            for k, v in enumerate(value):
                items.extend(http_build_query({str(k): v}, new_key).items())
        else:
            items.append((new_key, value))
    return dict(items)