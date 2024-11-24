from fastapi import FastAPI, Request


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "some message"}


@app.post("/")
async def body(request: Request):
    request_body = await request.json()
    print(request_body["key"])
    return {"key": f"{request_body['key']}"}
