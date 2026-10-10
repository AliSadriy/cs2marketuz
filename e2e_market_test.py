#!/usr/bin/env python3
"""Safe local staging test: seller listing -> buyer order -> mock pay -> mock trade -> seller payout."""
import json, os, sqlite3, urllib.request

BASE=os.getenv('E2E_BASE','http://127.0.0.1:8080').rstrip('/')
SELLER='8101'; BUYER='8102'; ADMIN='8199'
def call(path, method='GET', user=None, body=None):
    data=None if body is None else json.dumps(body).encode()
    headers={'Content-Type':'application/json'}
    if user: headers['X-Demo-User-Id']=user
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)
try:
    health=call('/api/health'); assert health['ok'] and health['market_items']>0
    sid=call('/api/skins?q=ak-47%20redline')['items'][0]['id']
    listing=call('/api/market/listings','POST',SELLER,{'skin_id':sid,'price':20.0})
    lid=listing['id']; assert listing['status']=='active'
    order=call('/api/market/orders','POST',BUYER,{'listing_id':lid})
    oid=order['id']; assert order['status']=='created'
    paid=call(f'/api/market/orders/{oid}/pay','POST',BUYER); assert paid['status']=='paid'
    trade=call(f'/api/market/orders/{oid}/trade','POST',BUYER); assert trade['status']=='sent'
    accepted=call(f"/api/market/trades/{trade['trade_id']}/accept",'POST',SELLER); assert accepted['order_status']=='delivered'
    balance=call('/api/market/balance','GET',SELLER); assert balance['available'] == 19.0
    payout=call('/api/market/payouts','POST',SELLER,{'amount':19.0}); assert payout['status']=='pending'
    decision=call(f"/api/admin/payouts/{payout['id']}/decision",'POST',ADMIN,{'action':'approve'}); assert decision['status']=='approved'
    print(json.dumps({'status':'OK','listing_id':lid,'order_id':oid,'trade_id':trade['trade_id'],'seller_balance':balance['available'],'payout_id':payout['id']}))
finally:
    db=os.path.join(os.path.dirname(__file__),'bot.db')
    con=sqlite3.connect(db)
    con.execute("DELETE FROM audit_log WHERE entity_type IN ('listing','order','payment','payout')")
    for table in ('trades','payout_requests','ledger','payments','orders','listings'):
        con.execute(f'DELETE FROM {table}')
    con.commit(); con.close()
