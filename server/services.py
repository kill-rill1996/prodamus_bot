import os
import hmac
import re
from datetime import datetime
from collections.abc import MutableMapping

from fastapi import Request, HTTPException
from prodamuspy import ProdamusPy
from logger import logger

from schemas import ResponseResultPayment, ResponseResultAutoPay
from settings import settings

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
        else: dictionary[key] = str(value)


async def verify(request):
    body = await request.json()
    request_sign = sign(body, settings.pay_token)
    return request.headers["sign"] == request_sign


async def verify_dict(body: dict, str_sign: str) -> bool:
    """Проверка подписи с помощью сторонней библиотеки для подготовки тела запроса"""
    request_sign = sign(body, settings.pay_token)
    return hmac.compare_digest(str_sign.lower(), request_sign)


async def get_body_params_pay_success(request: Request) -> ResponseResultPayment:
    """Для приема body у покупки подписки"""
    bodyDict = await verified_payload(request, "purchase")
    signIsGood = True

    # проверяем подписка с демо периодом или без
    is_trial: bool = True if bodyDict.get("subscription_demo_period") else False

    result = ResponseResultPayment(
        tg_id=bodyDict["order_num"],
        payment_status=bodyDict["payment_status"],
        sing_is_good=signIsGood,
        customer_phone=bodyDict["customer_phone"],
        profile_id=str(bodyDict["subscription"]["profile_id"]),
        date_last_payment=datetime.strptime(bodyDict["subscription"]["date_last_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        date_next_payment=datetime.strptime(bodyDict["subscription"]["date_next_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        is_trial=is_trial
    )

    return result


async def get_body_params_auto_pay(request: Request) -> ResponseResultAutoPay:
    """Для приема body у автопродления подписки"""
    bodyDict = await verified_payload(request, "auto")

    # логирование request body при ошибке
    if "error_code" in bodyDict["subscription"]:

        try:
            log_message = f"Ошибка при автоплатеже польз. tg_id {bodyDict['order_num']} " \
                          f"profile_id {bodyDict['subscription']['profile_id']}: {bodyDict['subscription']['error']}"

        except Exception as e:
            log_message = f"Ошибка при записи лога в автоплатеже: {e}"

        logger.error(log_message)

    signIsGood = True

    result = ResponseResultAutoPay(
        tg_id=bodyDict["order_num"],
        profile_id=str(bodyDict["subscription"]["profile_id"]),
        sing_is_good=signIsGood,
        customer_phone=bodyDict["customer_phone"],
        date_last_payment=datetime.strptime(bodyDict["subscription"]["date_last_payment"], '%Y-%m-%d %H:%M:%S'),    # '2024-12-26 22:08:59'
        date_next_payment=datetime.strptime(bodyDict["subscription"]["date_next_payment"], '%Y-%m-%d %H:%M:%S'),  # '2024-12-26 22:08:59'
        action_code=None,
        error_code=None,
        error=None,
        current_attempt=None,
        last_attempt=None,
        action_type=None,
    )

    # type = "notification" / "action"
    try:
        result.action_type = bodyDict["subscription"]["type"]
    except Exception:
        logger.error(f"В запросе отсутствует ключ type\n{bodyDict}")

    # для усп. платежей action_code='auto_payment',
    # для деактивации action_code='deactivation'
    try:
        result.action_code = bodyDict["subscription"]["action_code"]
    except Exception:
        pass

    try:
        result.last_attempt = bodyDict["subscription"]["last_attempt"]
    except Exception:
        pass

    # ошибка при платеже
    if "error_code" in bodyDict["subscription"]:
        try:
            result.error_code = bodyDict["subscription"]["error_code"]
            result.error = bodyDict["subscription"]["error"]
            result.current_attempt = bodyDict["subscription"]["current_attempt"]
        except Exception as e:
            logger.error(f"Ошибка при обработке НЕ успешного рекуррентного платежа:\n\n{e}")

    return result



async def verified_payload(request: Request, mode: str) -> dict:
    """Authenticate before parsing business fields or performing any side effects.

    Preserve the two signing formats already used by this deployed integration.
    The purchase signer escapes slashes; the existing recurring-payment signer
    does not. Never fall back to accepting an invalid signature.
    """
    cached = getattr(request.state, "verified_prodamus_payload", None)
    if cached is not None:
        return cached
    signature = request.headers.get("sign", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    body = await request.body()
    if len(body) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        prodamus = ProdamusPy(settings.pay_token)
        payload = prodamus.parse(body.decode("utf-8"))
        if mode == "purchase":
            valid = await verify_dict(payload, signature)
        else:
            valid = hmac.compare_digest(prodamus.sign(payload), signature.lower())
    except (ValueError, TypeError, UnicodeError, IndexError, RecursionError):
        raise HTTPException(status_code=400, detail="Invalid payload") from None
    if not valid:
        logger.warning("Rejected Prodamus webhook: invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    logger.info("Verified Prodamus webhook ({})", mode)
    request.state.verified_prodamus_payload = payload
    return payload
