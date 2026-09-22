"""Offline regression suite: no credentials, database or Telegram connection."""
import asyncio
import hashlib
import hmac
import json
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
SECRET = 'offline-test-secret'
sys.modules['settings'] = types.SimpleNamespace(settings=types.SimpleNamespace(pay_token=SECRET, channel_id='offline'))

class Engine:
    def __init__(self):
        self.receipts = set()
        self.locks = {}
        self.historical = False
    def begin(self):
        return Connection(self)

class Connection:
    def __init__(self, engine):
        self.engine = engine
        self.lock = None
        self.pending = None
    async def __aenter__(self):
        return self
    async def __aexit__(self, typ, value, tb):
        if typ is None and self.pending:
            self.engine.receipts.add(self.pending)
        if self.lock:
            self.lock.release()
    async def execute(self, sql, params=None):
        sql = str(sql)
        if 'pg_advisory_xact_lock' in sql:
            self.lock = self.engine.locks.setdefault(params['key'], asyncio.Lock())
            await self.lock.acquire()
        elif 'INSERT INTO webhook_receipts' in sql:
            self.pending = params['key']
    async def scalar(self, sql, params=None):
        if 'webhook_receipts' in str(sql):
            return params['key'] in self.engine.receipts
        return self.engine.historical

engine = Engine()
sys.modules['database'] = types.SimpleNamespace(async_engine=engine)
orm = types.SimpleNamespace(**{n: AsyncMock() for n in ['get_user_with_subscription_by_tg_id', 'update_user_phone', 'update_subscribe', 'add_operation', 'deactivate_subscription']})
sys.modules['orm'] = types.SimpleNamespace(AsyncOrm=orm)
message_names = ['send_error_message_to_user','send_invite_link_to_user','generate_invite_link','send_auto_pay_error_message_to_user','send_success_message_to_user','delete_user_from_channel','buy_subscription_error','send_error_message_to_admin']
messages = types.SimpleNamespace(**{n: AsyncMock() for n in message_names})
sys.modules['messages'] = messages
from fastapi import HTTPException
from starlette.requests import Request
import main
from services import verified_payload
from webhook_delivery import event_key


def payload():
    return {'order_id':'offline-order','order_num':'123','payment_status':'success','customer_phone':'offline', 'attempt':'1', 'subscription':{'profile_id':'offline-profile','date_last_payment':'2026-09-21 12:00:00','date_next_payment':'2026-10-21 12:00:00','type':'action','action_code':'auto_payment'}}


def make_request(data, mode='purchase', signature=None, missing=False):
    pairs = []
    def flatten(obj, prefix=''):
        if isinstance(obj, dict):
            for k,v in obj.items(): flatten(v, f'{prefix}[{k}]' if prefix else k)
        elif isinstance(obj, list):
            for i,v in enumerate(obj): flatten(v, f'{prefix}[{i}]')
        else: pairs.append((prefix,str(obj)))
    flatten(data)
    canonical=json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',',':'))
    if mode == 'purchase': canonical=canonical.replace('/', '\\/')
    signature=signature or hmac.new(SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    async def receive(): return {'type':'http.request','body':urlencode(pairs).encode(),'more_body':False}
    headers=[] if missing else [(b'sign',signature.encode())]
    return Request({'type':'http','method':'POST','path':'/offline','headers':headers},receive)

class WebhookTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        engine.receipts.clear(); engine.locks.clear(); engine.historical=False
        for m in vars(orm).values(): m.reset_mock()
        for m in vars(messages).values(): m.reset_mock()
        orm.get_user_with_subscription_by_tg_id.return_value=types.SimpleNamespace(id=1,tg_id='123',phone='offline',subscription=[types.SimpleNamespace(id=2)])
    async def test_invalid_purchase_has_no_side_effects(self):
        with self.assertRaises(HTTPException) as err:
            await main.buy_subscription(make_request(payload(),signature='0'*64))
        self.assertEqual(err.exception.status_code,403)
        for m in vars(orm).values(): m.assert_not_called()
        for m in vars(messages).values(): m.assert_not_called()
    async def test_invalid_auto_deactivation_has_no_side_effects(self):
        p=payload();p['subscription'].update(error='failed',last_attempt='yes',action_code='deactivation')
        with self.assertRaises(HTTPException):
            await main.auto_pay_subscription(make_request(p,'auto',signature='0'*64))
        for m in vars(orm).values(): m.assert_not_called()
        for m in vars(messages).values(): m.assert_not_called()
    async def test_missing_signature_rejected_before_business_fields(self):
        with self.assertRaises(HTTPException) as err:
            await main.buy_subscription(make_request({},missing=True))
        self.assertEqual(err.exception.status_code,403)
    async def test_valid_purchase_and_retry(self):
        p=payload()
        await main.buy_subscription(make_request(p))
        p['attempt']='2'
        self.assertEqual(await main.buy_subscription(make_request(p)),{'status':'duplicate'})
        orm.update_subscribe.assert_awaited_once()
        messages.send_invite_link_to_user.assert_awaited_once()
        self.assertEqual(orm.update_subscribe.call_args.kwargs['expire_date'],datetime(2026,10,22,13))
    async def test_valid_auto_payment(self):
        await main.auto_pay_subscription(make_request(payload(),'auto'))
        orm.update_subscribe.assert_awaited_once()
        messages.send_success_message_to_user.assert_awaited_once()
    async def test_concurrent_retry(self):
        await asyncio.gather(*(main.buy_subscription(make_request(payload())) for _ in range(5)))
        orm.update_subscribe.assert_awaited_once()
        messages.send_invite_link_to_user.assert_awaited_once()
    async def test_historical_payment_no_duplicate_message(self):
        engine.historical=True
        await main.buy_subscription(make_request(payload()))
        for m in vars(messages).values():m.assert_not_called()
        orm.update_subscribe.assert_not_called()
    async def test_failed_handler_is_not_marked_complete(self):
        orm.get_user_with_subscription_by_tg_id.side_effect=RuntimeError('offline temporary failure')
        try:
            with self.assertRaises(RuntimeError):await main.buy_subscription(make_request(payload()))
            self.assertFalse(engine.receipts)
        finally:orm.get_user_with_subscription_by_tg_id.side_effect=None
    async def test_purchase_unicode_slash_and_nested_products(self):
        p=payload();p['customer_extra']='Тариф / месяц';p['products']=[{'name':'Рацион / месяц','price':'100.00'}]
        self.assertEqual(await verified_payload(make_request(p),'purchase'),p)
    async def test_auto_legacy_signature_compatibility(self):
        p=payload();p['customer_extra']='Тариф / месяц'
        self.assertEqual(await verified_payload(make_request(p,'auto'),'auto'),p)
    async def test_signed_failed_payment_does_not_grant_access(self):
        p=payload();p['payment_status']='failed'
        await main.buy_subscription(make_request(p))
        orm.update_subscribe.assert_not_called()
        messages.send_invite_link_to_user.assert_not_called()
    def test_payment_attempts_are_distinct(self):
        p=payload();a=event_key(p,'auto');p['subscription']['current_attempt']='2'
        self.assertNotEqual(a,event_key(p,'auto'))

if __name__=='__main__':unittest.main()
