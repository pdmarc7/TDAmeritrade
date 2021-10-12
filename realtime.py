import urllib
import json
import requests
import joblib
import calendar
import time
import datetime
import logging
import decimal

import sys

import websockets
import asyncio

import dateutil.parser
import trade as td

import realtime_risk_management as rt
import risk_management as rma

import pandas as pd

today = datetime.date.today()
today_time = time.ctime()

day = calendar.weekday(today.year, today.month, today.day)


LOG_FILENAME = 'logs/{}-{}-{}.log'.format(today.day, today.month, today.year)
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
)


if td.holiday():
    logging.info("{} : Its a Holiday! Markets are Closed".format(today))
    sys.exit(0)

days = [5, 6] #trade only on tuesdays and thursdays

#check the day before processing; Analytics can only occur from Monday to Friday
if day in days:
    logging.info("{} : Not Allowed to Trade Today".format(today))
    sys.exit(0)

access_token = td.get_access_token()

def unix_time_milliseconds(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds() * 1000.0


endpoint = 'https://api.tdameritrade.com/v1/userprincipals'
params = {'fields': 'streamerSubscriptionKeys,streamerConnectionInfo'}

content = requests.get(url = endpoint, params = params, headers = access_token)
userPrincipalsResponse =  content.json()


tokenTimeStamp = userPrincipalsResponse['streamerInfo']['tokenTimestamp']
date = dateutil.parser.parse(tokenTimeStamp, ignoretz = True)
tokenTimeStampAsMs = unix_time_milliseconds(date)

symbol, prediction = joblib.load("symbol.pk")

#performing some needed technical analysis
header = td.get_access_token()
history = td.get_history(symbol, header)
#getting the minute_by_minute atr
tech_analysis = rma.technical_analysis(history, history["close"], history["high"], history["low"])
atr = round(tech_analysis["AVERAGE TRUE RANGE"].tail(1).item(), 4)

if symbol == None or prediction == None:
    logging.info("The order.py script was did not complete functioning")
    sys.exit(0)

credentials = {"userid": userPrincipalsResponse['accounts'][0]['accountId'],
               "token": userPrincipalsResponse['streamerInfo']['token'],
               "company": userPrincipalsResponse['accounts'][0]['company'],
               "segment": userPrincipalsResponse['accounts'][0]['segment'],
               "cddomain": userPrincipalsResponse['accounts'][0]['accountCdDomainId'],
               "usergroup": userPrincipalsResponse['streamerInfo']['userGroup'],
               "accesslevel":userPrincipalsResponse['streamerInfo']['accessLevel'],
               "authorized": "Y",
               "timestamp": int(tokenTimeStampAsMs),
               "appid": userPrincipalsResponse['streamerInfo']['appId'],
               "acl": userPrincipalsResponse['streamerInfo']['acl'] }

login_request = {
    "requests": [
            {
                "service": "ADMIN",
                "command": "LOGIN",
                "requestid": 0,
                "account": userPrincipalsResponse['accounts'][0]['accountId'],
                "source": userPrincipalsResponse['streamerInfo']['appId'],
                "parameters": {
                    "credential": urllib.parse.urlencode(credentials),
                    "token": userPrincipalsResponse['streamerInfo']['token'],
                    "version": "1.0"
                }
            }
    ]
}

qos_request = {
        "requests": [
            {
                "service": "ADMIN",
                "requestid": "2",
                "command": "QOS",
                "account": userPrincipalsResponse['accounts'][0]['accountId'],
                "source": userPrincipalsResponse['streamerInfo']['appId'],
                "parameters": {
                    "qoslevel": "0"
                }
            }
    ]
}

market_request = {
        "requests": [
            {
                "service": "CHART_EQUITY",
                "requestid": "2",
                "command": "SUBS",
                "account": userPrincipalsResponse['accounts'][0]['accountId'],
                "source": userPrincipalsResponse['streamerInfo']['appId'],
                "parameters": {
                    "keys": symbol,
                    "fields": "0,1,2,3,4,5,6,7,8"
                }
            }
    ]
}


logging.info("{}:  Initializing Realtime Monitoring Engine".format(time.ctime()))

dataset = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
async def main():
    uri = "wss://" + userPrincipalsResponse["streamerInfo"]["streamerSocketUrl"] + "/ws"
    async with websockets.connect(uri) as websocket:
        try:
            await websocket.send(json.dumps(login_request))
            response = await websocket.recv()
            print(response)

            #await websocket.send(json.dumps(qos_request))
            #response = await websocket.recv()
            #print(response)
            
            await websocket.send(json.dumps(market_request))
            while True:
                res = await websocket.recv()
                response = json.loads(res)
                
                #check for market close
                if td.time_check() == "closed":
                    logging.info("{}: The Markets are Closed".format(time.ctime()))
                    sys.exit(0)
                
                if "data" in response.keys():
                    open_price = response["data"][0]['content'][0]["1"]
                    high_price = response["data"][0]['content'][0]["2"]
                    low_price = response["data"][0]['content'][0]["3"]
                    close_price = response["data"][0]['content'][0]["4"]
                    volume = response["data"][0]['content'][0]["5"]

                    logging.info("{}: {}, {}, {}, {}, {}".format(time.ctime(), open_price, \
                        high_price, low_price, close_price, int(volume)))

                    if dataset.empty:
                        dataset.loc[0] = [open_price, high_price, \
                        low_price, close_price, int(volume)]
                        
                    else:
                        index = dataset.tail(1).index.item()
                        dataset.loc[index + 1] = [open_price, high_price, low_price, close_price, int(volume)]
                        if dataset.count()["open"] > 10:
                            analysis = rt.technical_analysis(dataset, dataset["close"], \
                                dataset["high"], dataset["low"])
                            logging.info("{}:   Open: {}, High: {}, Low: {}, Close: {}, RSI: {}, Stochastic %D Line: {}, Stochastic %K Line: {}, Buy-Signal: {}, Sell-Signal: {}".format(
                                time.ctime(),
                                analysis.tail(1)["open"].item(),  
                                analysis.tail(1)["high"].item(),  
                                analysis.tail(1)["low"].item(),  
                                analysis.tail(1)["close"].item(),  
                                analysis.tail(1)["RSI"].item(),  
                                analysis.tail(1)["STOCHASTIC %D LINE"].item(),
                                analysis.tail(1)["STOCHASTIC %K LINE"].item(),
                                analysis.tail(1)["BUY-SIGNAL"].item(), 
                                analysis.tail(1)["SELL-SIGNAL"].item()
                                )
                            )
                            try:                                
                                buy_signal = analysis.tail(1)["BUY-SIGNAL"].item()
                                #sell_signal =  analysis.tail(1)["SELL-SIGNAL"].item()  
                                logging.info("{}: Signal Quality: {}".format(time.ctime(), buy_signal))

                                if buy_signal == True and  analysis.tail(1)["STOCHASTIC %D LINE"].item() > 5:
                                    #trade strategy
                                    header = td.get_access_token()
                                    quote = td.get_quote(symbol, header)

                                    buyprice = quote[symbol]["askPrice"]
                                                                
                                    sellprice = buyprice + round(atr, decimal.Decimal(str(buyprice)).as_tuple().exponent * -1)

                                    dp = round(atr, decimal.Decimal(str(buyprice)).as_tuple().exponent * -1)

                                    if sellprice == buyprice:
                                        if dp == 2:
                                            sellprice = sellprice + 0.01

                                        if dp == 3:
                                            sellprice = sellprice + 0.001

                                        if dp == 4:
                                            sellprice = sellprice + 0.0001

                                    if sellprice > buyprice:
                                        td.order(symbol, buyprice, sellprice)

                                        logging.info("{}: Conditional Buy-Sell Order Placed -- Symbol: {}, BuyPrice: {}, SellPrice: {}".format(time.ctime(), symbol, buyprice, sellprice))
                                        sys.exit(0)
                                    else:
                                        logging.info("{}: BuyPrice Is Greater Than Sell Price -- Symbol: {}, BuyPrice: {}, SellPrice: {}".format(time.ctime(), symbol, buyprice, sellprice))
                                else:
                                    logging.info("{}: Buy Signal Is False -- Buy Signal: {}".format(time.ctime(), buy_signal))


                                #check if market is closed
                                if td.time_check() == "closed":
                                    sys.exit(0)

                            except Exception as e:
                                print(e)                    
                
                if "notify" in response.keys():
                    await websocket.ping()
                    logging.info("Sent Keep Alive Ping Packet")    

        except Exception as e:
            print(e)
        
asyncio.get_event_loop().run_until_complete(main())
