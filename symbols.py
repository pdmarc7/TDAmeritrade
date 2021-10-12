import risk_management as rma
import trade as td
import joblib
import datetime
import time
import sys
import calendar
import logging

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

days = [5, 6] #trade only on tuesdays, and thursdays

#check the day before processing; Analytics can only occur from Monday to Thursday
if day in days:
    logging.info("{} : Not Allowed to Trade Today".format(today))
    sys.exit(0)

symbols = rma.get_symbols()

def quote(symbol):
    try:
        header = td.get_access_token()
        q = td.get_quote(symbol, header)

        print(f"Processing symbol {symbol}")
        
        time.sleep(1)
        if  q[symbol]["askPrice"] > 0.2 and q[symbol]["askPrice"] < 1:
            logging.info("Processing symbol {} with quote {}".format(symbol, q[symbol]["askPrice"]))
            return symbol
    except Exception as e:
        logging.info("Error on symbol {}: {}".format(symbol, e))
        return None

def acquisition():
    approved_equities = list()
    logging.info("{}: Beginning Stock List Acquisition".format(time.ctime()))

    for symbol in symbols:
        qt = quote(symbol)
        time.sleep(2)
        if qt == None:
            continue
        else:
            approved_equities.append(symbol)

    joblib.dump(approved_equities, "daily_symbols.pk")
    joblib.dump([None, None], "symbol.pk")
    logging.info(f"{time.ctime()}: Stock List Acquisition Complete")
    return None

acquisition()

