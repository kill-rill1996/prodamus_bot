from fastapi import FastAPI, Request, Response
from prodamuspy import ProdamusPy

from orm import AsyncOrm

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "some message"}


@app.post("/")
async def body(request: Request):
    request_params = await get_body_params(request)
    user = await AsyncOrm.get_user_with_subscription_by_tg_id(request_params["order_num"])

    await AsyncOrm.update_subscribe(user.subscription[0].id)


async def get_body_params(request: Request) -> dict:
    prodamus = ProdamusPy("aaf95a836e6c3c03c30dbca198ec807166097659509246d14db70564960839a3")

    body = await request.body()
    bodyDict = prodamus.parse(body.decode())
    print(f"DECODED BODY: {bodyDict}")

    # TODO доделать проверку и не возвращать если подделка
    signIsGood = prodamus.verify(bodyDict, request.headers["sign"])
    print(signIsGood)

    result = {
        "order_num": bodyDict["order_num"],
        "payment_status": bodyDict["payment_status"],
        "received_sign": request.headers["Sign"]
    }

    return result
