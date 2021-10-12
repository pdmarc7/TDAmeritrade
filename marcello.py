#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 15:24:48 2020

@author: dave
"""

import trade as td
import datetime
import time
import sys
import calendar
import logging
import joblib
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

#check the day before processing; Analytics can only occur from Monday to Thursday
if day in days:
    logging.info("{} : Not Allowed to Trade Today".format(today))
    sys.exit(0)

def processing(symbol):
    try:
        header = td.get_access_token()
        history = td.get_daily_history(symbol, header)

        ####------making sure there's no PIT errors------#####
        #timestamp = history.tail(1)["datetime"].item()

        #previous_day = datetime.date.today() - datetime.timedelta(days=1)
        #history_previous_day = datetime.datetime.fromtimestamp(timestamp/1000).date()

        #if previous_day == history_previous_day:
        #    pass
        #else:
        #    return None
        ####------making sure there's no PIT errors------#####

        #quote = td.get_quote(symbol, header)
        #volume = history.tail(1)["volume"].item()

        history_ta = rma.technical_analysis(history, history["close"], history["high"], history["low"])
        #history_ta.to_csv("data/{}".format(symbol))
        signal = history_ta["SIGNAL"].tail(1).item()
        signal_freq = history_ta["SIGNAL"].value_counts(normalize=True)[1]
        logging.info("SYMBOL: {}, SIGNAL: {}, SIGNAL_FREQUENCY: {}".format(symbol, signal, signal_freq))
        time.sleep(2)
        return {"SYMBOL": symbol, "SIGNAL": signal, "SIGNAL_FREQUENCY": signal_freq}
    except:
        return None
    
def analyze():    
    analysis = list()
    symbols = joblib.load("daily_symbols.pk")
    
    for symbol in symbols:
        try:
            data = processing(symbol)
            if data == None:
                continue
            else:
                analysis.append(data)
        except Exception as e:
            logging.info("{}: {}".format(symbol, e))
                
    data = pd.DataFrame(analysis, columns=["SYMBOL", "SIGNAL", "SIGNAL_FREQUENCY"])
    joblib.dump(data, "data.pk")
    results = data.query("SIGNAL == 1").query("SIGNAL_FREQUENCY > 0.2").sort_values(by=["SIGNAL_FREQUENCY"], ascending=False)
    results.to_csv("results.csv")
    return results

logging.info("{} : Registering Analytics Execution".format(time.ctime()))

results = analyze()
joblib.dump(results, "results.pk")

logging.info("{} : Analysis Execution Complete".format(time.ctime()))
