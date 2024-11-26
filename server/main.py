from fastapi import FastAPI, Request, Response

from prodamuspy import ProdamusPy

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "some message"}


@app.post("/")
async def body(request: Request):
    print(f"Запрос от {request.url}\n")

    body = await request.body()
    print(f"BODY {body.decode()}\n")

    print(f"HEADERS: {request.headers}\n")

    try:
        received_sign = request.headers["Sign"] #'sign': 'a543ce34b6b44f1fb7489e2af616952fa0197a0af685e79e16f9101b8a6ec4e6'
        print(f"recieved sign: {received_sign}\n")
    except:
        print(f"Не получилось получить SIGN\n")

    prodamus = ProdamusPy("aaf95a836e6c3c03c30dbca198ec807166097659509246d14db70564960839a3")
    try:
        bodyDict = prodamus.parse(body.decode())
        print(f"DECODED BODY: {bodyDict}")

        try:
            signIsGood = prodamus.verify(bodyDict, request.headers["sign"])
            print(f"SIGN RESULT: {signIsGood}")
        except:
            print(f"Не получилось выполнить prodamus.verify(bodyDict, received_sign)")

    except:
        print("Не получилось сделать prodamus.parse() из body.decode()!!!\n")


    # print(request_body["key"])
    # sing = await get_body_params(request)
    # print(sing)
    # return {"key": f"{request_body['key']}"}


async def get_body_params(request: Request):
    prodamus = ProdamusPy("API KEY")
    body = await request.body()
    # print(body)
    bodyDict = prodamus.parse(body.decode())

    receivedSign = request.headers["Sign"]

    signIsGood = prodamus.verify(bodyDict, receivedSign)
    print(signIsGood)

    print(bodyDict)

    # return sign
