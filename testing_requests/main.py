import asyncio
import os
from collections.abc import MutableMapping
from dotenv import load_dotenv

import aiohttp


async def main():
    load_dotenv()
    cookies = {"referer": "YTozOntzOjM6InVybCI7czowOiIiO3M6Mzoic3lzIjtzOjA6IiI7czozOiJrd2QiO3M6MDoiIjt9",
               "session": "t1qakve4s4rujega19qrnv5rp4"}

    async with aiohttp.ClientSession(cookies=cookies) as session:
        link_form = "https://sheva-nutrition.payform.ru/"
        token = os.getenv("PAY_TOKEN")
        print(token)
        print("TESTING REQ")

        data = {"order_id": 714371204, "subscription": 2093463, "customer_extra": "Информация об оплачиваемой подписке",
            "do": "link", "sys": ""}

        signature = sign(data, token)
        data["signature"] = signature

        async with session.get(link_form, params=data) as resp:
            print(resp.status)
            print(await resp.text())


def sign(data, secret_key):
    import hashlib
    import hmac
    import json

    deep_int_to_string(data)

    data_json = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).replace("/", "\\/")

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


asyncio.run(main())
