import json, os, re, urllib.request, urllib.parse, datetime

ROOT=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(ROOT,'prices.json')

# These are the default holdings. The app can add more symbols later; this daily job
# focuses on the user's initial three symbols plus USD/TWD.
TICKERS=['2330.TW','00981A.TW','TSMY']

def get_json(url):
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 investment-pwa/5'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def yahoo(symbol):
    url='https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(symbol,safe='')+'?range=5d&interval=1d&events=history'
    j=get_json(url)
    result=(j.get('chart') or {}).get('result') or []
    if not result: raise RuntimeError('Yahoo 無資料')
    r=result[0]
    ts=r.get('timestamp') or []
    closes=((r.get('indicators') or {}).get('quote') or [{}])[0].get('close') or []
    for i in range(len(ts)-1,-1,-1):
        if i < len(closes) and closes[i] is not None:
            d=datetime.datetime.fromtimestamp(ts[i], datetime.timezone.utc).date().isoformat()
            return float(closes[i]), d, 'Yahoo Finance'
    raise RuntimeError('Yahoo 無收盤價')

def twse_all():
    url='https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
    data=get_json(url)
    return {str(x.get('Code','')).strip(): x for x in data if x.get('Code')}

def main():
    data={'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'fx':{}, 'prices':{}, 'errors':{}}
    # USD/TWD from Yahoo (server-side, so no browser CORS issue)
    try:
        p,d,s=yahoo('TWD=X')
        data['fx']['USD_TWD']={'value':p,'date':d,'source':s}
    except Exception as e:
        data['errors']['USD_TWD']=str(e)

    tw=None
    try: tw=twse_all()
    except Exception as e:
        data['errors']['TWSE']=str(e)

    for t in TICKERS:
        try:
            if t.endswith('.TW') and tw is not None:
                code=t[:-3]
                row=tw.get(code)
                if not row:
                    raise RuntimeError('TWSE 找不到代號 '+code)
                close=row.get('ClosingPrice')
                if close in (None,'','-'):
                    raise RuntimeError('TWSE 無收盤價')
                # TWSE API date is in Minguo year format in some feeds; use update day as published date.
                d=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
                data['prices'][t]={'price':float(str(close).replace(',','')),'date':d,'currency':'TWD','source':'TWSE OpenAPI'}
            else:
                p,d,s=yahoo(t)
                data['prices'][t]={'price':p,'date':d,'currency':'USD','source':s}
        except Exception as e:
            data['errors'][t]=str(e)

    with open(OUT,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
