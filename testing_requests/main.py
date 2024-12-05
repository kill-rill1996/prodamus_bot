import asyncio

import aiohttp


async def main():
    async with aiohttp.ClientSession() as session:
        link_form = "https://sheva-nutrition.payform.ru/"
        print("TESTING REQ")

        data = {"order_id": 714371204, "subscription": 2093463, "customer_extra": "Информация об оплачиваемой подписке",
            "do": "link", "sys": ""}

        async with session.get(link_form, params=data) as resp:
            print(resp.status)
            print(await resp.text())


asyncio.run(main())
