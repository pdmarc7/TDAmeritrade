# coding: utf-8
from config import clientid,account
import requests
import urllib
import time
import logging
import pandas as pd
import datetime
import webbrowser
import sys

today = datetime.date.today()

LOG_FILENAME = 'logs/{}-{}-{}.log'.format(today.day, today.month, today.year)
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
)


def get_url():
    redirect_url = "http://localhost/"
    url = " https://auth.tdameritrade.com/auth?response_type=code&redirect_uri={}&client_id={}%40AMER.OAUTHAP".format(redirect_url, clientid)
    return webbrowser.open(url)


def get_new_access_token(new_url): 
    parse_url = urllib.parse.unquote(new_url.split('code=')[1]) 
 
    header = {'Content-Type': "application/x-www-form-urlencoded"} 

    payload = {'grant_type':'authorization_code',  
               'access_type':'offline', 
               'client_id':clientid + "@AMER.OAUTHAP",  
               'code': parse_url, 
               'redirect_uri':'http://localhost/', 
 	} 
  
    url = 'https://api.tdameritrade.com/v1/oauth2/token' 

    authReply = requests.post(url, headers=header, data=payload) 
    response = authReply.json() 

    return response 



def get_access_token():
    tokens = "<-- access_token -->"


    payload = {'grant_type':'refresh_token', 'refresh_token':tokens["refresh_token"], 'client_id':clientid}
    authReply = requests.post('https://api.tdameritrade.com/v1/oauth2/token', data=payload)
    response = authReply.json()

    access_token = response["access_token"]
    header = {'Authorization':'Bearer {}'.format(access_token)}
    
    return header



def get_account_balance(header):
    endpoint = "https://api.tdameritrade.com/v1/accounts/{}".format(account)
    
    content = requests.get(url = endpoint, headers = header)
    data = content.json()
    
    cash_balance = data['securitiesAccount']['initialBalances']
    
    return cash_balance
    


def place_order(symbol, buyprice, sellprice, quantity, header):
    header["Content-Type"] = "application/json"
    endpoint = "https://api.tdameritrade.com/v1/accounts/{}/orders".format(account)
    canceltime = str(datetime.date.today() + datetime.timedelta(weeks = 1))
    
    payload = {
      "orderType": "LIMIT",
      "session": "NORMAL",
      "price": buyprice,
      "duration": "DAY",
      "orderStrategyType": "TRIGGER",
      "orderLegCollection": [
        {
          "instruction": "BUY",
          "quantity": quantity,
          "instrument": {
            "symbol": symbol,
            "assetType": "EQUITY"
          }
        }
      ],
      "childOrderStrategies":  [
        {
          "orderType": "LIMIT",
          "session": "NORMAL",
          "price": sellprice,
          "duration": "GOOD_TILL_CANCEL",
          "cancelTime": canceltime,
          "orderStrategyType": "SINGLE",
          "orderLegCollection": [
            {
              "instruction": "SELL",
              "quantity": quantity,
              "instrument": {
                "symbol": symbol,
                "assetType": "EQUITY"
              }
            }
          ]
        }
      ]
    }
    
    content = requests.post(url = endpoint, json = payload, headers = header)
    
    if content.status_code == 200 or content.status_code == 201:
        return True
    else:
        return False


def place_buy_order(symbol, price):
    header = get_access_token()
    header["Content-Type"] = "application/json"
    endpoint = "https://api.tdameritrade.com/v1/accounts/{}/orders".format(account)
    
    balance = get_account_balance(header)
    tradingCash = balance['cashAvailableForTrading']
   
    quantity = int(tradingCash/price)
    
    payload = {
          "orderType": "LIMIT",
          "session": "NORMAL",
          "price": price,
          "duration": "DAY",
          "orderStrategyType": "SINGLE",
          "orderLegCollection": [
            {
              "instruction": "BUY",
              "quantity": quantity,
              "instrument": {
                "symbol": symbol,
                "assetType": "EQUITY"
              }
            }
          ]
        }
    
    if quantity > 0:
        content = requests.post(url = endpoint, json = payload, headers = header)
        if content.status_code == 200 or content.status_code == 201:
            logging.info("{}: Buy order placed for symbol: {}, buyprice: {}, shares: {}"\
                      .format(time.ctime(), symbol, price, quantity)) 
            return True
        else:
            return False  
    else:
        logging.info("{} : Unable to place Order BUY for symbol: {}, sellprice: {}, shares: {}"\
                      .format(time.ctime(), symbol, price, quantity))

def place_sell_order(symbol, price, quantity):
    header = get_access_token()
    header["Content-Type"] = "application/json"
    endpoint = "https://api.tdameritrade.com/v1/accounts/{}/orders".format(account)
    
    payload = {
		  "orderType": "LIMIT",
		  "session": "NORMAL",
		  "price": price,
		  "duration": "GOOD_TILL_CANCEL",
		  "orderStrategyType": "SINGLE",
          "orderLegCollection": [
            {
              "instruction": "SELL",
              "quantity": quantity,
              "instrument": {
                "symbol": symbol,
                "assetType": "EQUITY"
              }
            }
          ]
        }        
        
    content = requests.post(url = endpoint, json = payload, headers = header)
    
    if content.status_code == 200 or content.status_code == 201:
        logging.info("{}: Sell order placed for symbol: {}, sellprice: {}, shares: {}"\
                      .format(time.ctime(), symbol, price, quantity)) 
        return True
    else:
        return False



def order(symbol, buyprice, sellprice):
    header = get_access_token()
    
    balance = get_account_balance(header)
    tradingCash = balance['cashAvailableForTrading']
   
    quantity = int(tradingCash/buyprice)
    
    if quantity > 0:
        order_status = place_order(symbol, buyprice, sellprice, quantity, header)
        if order_status == True:
            logging.info("{}: Conditional BUY/SELL order placed for symbol: {}, buyprice: {}, sellprice: {}, stop: {},shares: {}"\
                      .format(time.ctime(), symbol, buyprice, sellprice, quantity))
    else:
        logging.info("{} : Unable To Place Order Conditional BUY/SELL For Symbol: {}, buyprice: {}, sellprice: {}, shares: {}"\
                      .format(time.ctime(), symbol, buyprice, sellprice, quantity))

        

def get_history(symbol, header):
    endpoint = "https://api.tdameritrade.com/v1/marketdata/{}/pricehistory".format(symbol)
    params = {'apikey':clientid, 'periodType':'day', 'frequencyType':'minute', 'frequency':1, 'period':'10', 'needExtendedHoursData':'true'}
    
    content = requests.get(url = endpoint,params=params)
    data = content.json()

    info = []

    for inf in data["candles"]:
        info.append(inf.values())

    df = pd.DataFrame(info, columns=['open', 'high', 'low', 'close', 'volume', 'datetime'])

    return df



def get_daily_history(symbol, header):
    endpoint = "https://api.tdameritrade.com/v1/marketdata/{}/pricehistory".format(symbol)
    params = {'apikey':clientid, 'periodType':'year', 'frequencyType':'daily', 'frequency':1, 'period':'20', 'needExtendedHoursData':'true'}

    content = requests.get(url = endpoint,params=params)
    data = content.json()

    info = []

    for inf in data["candles"]:
        info.append(inf.values())

    df = pd.DataFrame(info, columns=['open', 'high', 'low', 'close', 'volume', 'datetime'])

    return df

    

def get_order_status(header):
    endpoint = "https://api.tdameritrade.com/v1/orders/"
    
    payload = {'accountId': account}

    content = requests.get(url=endpoint, headers=header, params=payload)
    data = content.json()
    
    return data

def get_order_by_path():
    header = get_access_token()
    endpoint = "https://api.tdameritrade.com/v1/accounts/{}/orders/".format(account)

    payload = {
		"fromEnteredTime": str(datetime.date.today() - datetime.timedelta(weeks=2)),
        "toEnteredTime": str(datetime.date.today())
		}

    content = requests.get(url=endpoint, headers=header, params=payload)
    data = content.json()

    return data

    
def get_quote(symbol, header):
    endpoint = "https://api.tdameritrade.com/v1/marketdata/{}/quotes".format(symbol)
    payload = {'apikey': clientid}

    content = requests.get(url = endpoint, headers=header, params=payload, timeout=5)
    data = content.json()
    
    return data


def get_alpha_quote(symbol):
    endpoint = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={}&apikey=JGBQ00YKXPR3PQNT".format(symbol)
    
    content = requests.get(url =endpoint)
    data = content.json()
    
    return data


def holiday():
    today = datetime.date.today()
    #using NASDAQ schedule for the year
    day = [today.day, today.month]
    holidays = ([1, 1], [20, 1], [17, 2], [10, 4], [25, 5], [3, 7], [7, 9], [26, 11], [27, 11], [24, 12], [25, 12])
    
    if day in holidays:
        return True
    else:
        return False

def time_check():
    today = datetime.datetime.today()
    open_hours = datetime.time(13, 30, 0)
    close_hours = datetime.time(21, 0, 0)

    market_open = datetime.datetime.combine(today, open_hours)
    market_close =  datetime.datetime.combine(today, close_hours)

    if datetime.datetime.now() > market_open and datetime.datetime.now() < market_close:
        return "open"
    elif datetime.datetime.now() < market_open and datetime.datetime.now() < market_close:
        return "pending"
    elif datetime.datetime.now() > market_open and datetime.datetime.now() > market_close:
        return "closed"



    
