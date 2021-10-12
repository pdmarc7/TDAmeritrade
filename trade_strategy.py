import time
import datetime

import logging

import trade as td
import joblib as jb

import sys

#import asyncio

today = datetime.date.today()

LOG_FILENAME = 'logs/{}-{}-{}.log'.format(today.day, today.month, today.year)
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
)

async def verify_prediction_status(symbol, prediction):
    #exit strategy no. 2
    header = td.get_access_token()
    quote = td.get_quote(symbol, header)

    buyprice = quote[symbol]["askPrice"]    
    sellprice = buyprice + 0.01

    if td.time_check() == "open" and prediction > buyprice:
        order = td.order(symbol, buyprice, sellprice)
        if order == True:
            logging.info("{}: Placing Conditional Buy-Sell Order -- Symbol: {}, BuyPrice: {}, SellPrice: {}".format(time.ctime(), symbol, buyprice, sellprice))
        else:
            logging.info("{}: Unable to execute sell order, Order Function Returned False".format(time.ctime()))
            return False
    else:
        logging.info("{}: Unable to execute sell order".format(time.ctime()))
        return False


async def trade_strategy(symbol):
    #exit strategy no. 2
    header = td.get_access_token(); quote = td.get_quote(symbol, header)

    #account_balance = td.get_account_balance(header)["cashAvailableForTrading"]

    #three_percent_of_account_value = account_balance * 0.03
    #two_percent_of_account_value = account_balance * 0.02    

    buyprice = quote[symbol]["askPrice"]
    #quantity = int(account_balance/buyprice)
    
    #value_per_share = two_percent_of_account_value/quantity
    sellprice = quote[symbol]["bidPrice"] + 0.01

    #stop_per_share = two_percent_of_account_value/quantity
    #stoploss = quote[symbol]["bidPrice"] - stop_per_share

    #if buyprice > 1:
    #    sellprice = round(sellprice, 2); stoploss = round(stoploss, 2)
    #elif buyprice < 1:
    #    sellprice = round(sellprice, 4); stoploss = round(stoploss, 4)
        
    if td.time_check() == "open":
        td.order(symbol, buyprice, sellprice)
        logging.info("{}: Placing Conditional Buy-Sell Order -- Symbol: {}, BuyPrice: {}, SellPrice: {}".format(time.ctime(), symbol, buyprice, sellprice))
        return True
    else:
        logging.info("{}: Unable to execute sell order".format(time.ctime()))
        return False

