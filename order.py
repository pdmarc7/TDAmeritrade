import trade as td
import datetime
import time
import sys
import calendar
import logging
import joblib
import os
import risk_management as rma
import prediction as pred
import pandas as pd
import ta

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

try:
    logging.info("{} : Initializing Order Mangement".format(time.ctime()))
    data = joblib.load("results.pk"); ml = list()

    
    for symbol in data["SYMBOL"]:
        try:
            prediction, mse, score = pred.process(symbol)
            ml.append([symbol, prediction, mse, score])
        except:
            pass

    ml_df = pd.DataFrame(ml, columns=["SYMBOL", "PREDICTION", "MSE", "SCORE"])
    ml_df["ASKPRICE"] = ml_df["SYMBOL"].apply(rma.get_askprice)

    result = ml_df.query("ASKPRICE > 0.2").query("ASKPRICE < 5").query("PREDICTION > ASKPRICE").query("SCORE > 0.98").sort_values(by=["MSE"])

    result.to_csv("order.csv")

    symbol, prediction = result.head(1)["SYMBOL"].item(), result.head(1)["PREDICTION"].item()
    joblib.dump([symbol, prediction], "symbol.pk")
    #os.remove("results.pk")
    
    logging.info("{} : Predictive Analytics Complete ".format(time.ctime()))
except Exception as e:
    logging.info("{} : Code Exception On Order Placement: {}".format(time.ctime(), e))
