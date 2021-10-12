from ftplib import FTP
import yfinance as yf
import pandas as pd
import numpy as np
import trade as td
import datetime
import time
import ta
import sys
import logging
import os
from decimal import Decimal, ROUND_DOWN
from multiprocessing import Pool
from collections import Counter

today = datetime.date.today()

LOG_FILENAME = 'logs/{}-{}-{}.log'.format(today.day, today.month, today.year)
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
)


###############################################################################
    
                        #SUPPORTING FUNCTIONS

###############################################################################
def technical_analysis(data, close, high, low):
    #TREND ANALYSIS
    adx = ta.trend.ADXIndicator(high, low, close, n = 14, fillna = True)
    bollinger = ta.volatility.BollingerBands(close, n = 20, ndev = 2, fillna = True)
    #OSCILLATORS
    rsi = ta.momentum.RSIIndicator(close, n = 14, fillna = True)
    stochastic = ta.momentum.StochasticOscillator(high, low, close, n = 14, d_n = 3, fillna = True)
    #AVERAGE TRUE RANGE
    data['AVERAGE TRUE RANGE'] =  ta.volatility.average_true_range(high, low, close, n=14, fillna=True)
    #BOLLINGER BANDS
    data['BOLLINGER HIGH'] = bollinger.bollinger_hband()
    data['BOLLINGER LOW'] = bollinger.bollinger_lband()
    data['BOLLINGER MIDDLE']= bollinger.bollinger_mavg()
    #AVERAGE DIRECTIONAL INDEX
    data['ADX'] = adx.adx()
    data['+DI'] = adx.adx_pos()
    data['-DI'] = adx.adx_neg()
    #RELATIVE STRENGTH INDEX
    data['RSI'] = rsi.rsi()
    #STOCHASTICS
    data['STOCHASTIC %K LINE'] = stochastic.stoch()
    data['STOCHASTIC %D LINE'] = stochastic.stoch_signal()
    #DIRECTIONAL MOVEMENT INDEX SIGNALS
    data['DI SIGNAL'] = np.where(data['+DI'] > data['-DI'], 1, 0)
    #OSCILLATOR BUY SIGNALS
    data['RSI BUY SIGNAL'] = np.where(data["RSI"] < 50, 1, 0)
    data['STOCHASTIC SIGNAL'] = np.where(data["STOCHASTIC %D LINE"] < 20, 1, 0)
    data['STOCHASTIC BUY SIGNAL'] = np.where(data["STOCHASTIC %D LINE"] < 20, 1, 0)
    #SIGNAL
    data['SIGNAL'] = np.where(data["STOCHASTIC BUY SIGNAL"] * data["RSI BUY SIGNAL"] == 1, 1, 0)
    return data


def get_stoploss(symbol):
    header = td.get_access_token()
    data = td.get_daily_history(symbol, header)
    ###################################################################################
    processed_data = technical_analysis(data, data["close"], data["high"], data["low"])
    ###################################################################################
    return processed_data["AVERAGE TRUE RANGE"].tail(1).item()

def signal(symbol):
    data = pd.read_csv("data/{}".format(symbol))
    tech_analysis = technical_analysis(data, data['close'], data['high'], data['low'])
    index = data.tail(1).index.start

    if tech_analysis.iloc[index]["SIGNAL"] == 1 and \
    tech_analysis.iloc[index]["DI SIGNAL"] == 1 and \
    tech_analysis.iloc[index]["RSI BUY SIGNAL"] == 1 and \
    tech_analysis.iloc[index]["AVERAGE TRUE RANGE"] > 0.1:
        return 1
    else:
        return 0
    
def bid_ask_spread(symbol):
    header = td.get_access_token()
    symbol_quote = td.get_quote(symbol, header)
    time.sleep(3)
    try:
        askprice = symbol_quote[symbol]['askPrice']
        bidprice = symbol_quote[symbol]['bidPrice']
        spread = askprice - bidprice
        return spread
    except:
        return -1
    
def signal_quality(symbol):
    data = pd.read_csv("data/{}".format(symbol))
    tech_analysis = technical_analysis(data, data['close'], data['high'], data['low'])
    index = data.tail(1).index.start

    previous_signal = tech_analysis.iloc[index - 1]["SIGNAL"]
    
    if previous_signal == 0:
        return 1
    else:
        return 0
    
def position_freq(symbol):
    data = pd.read_csv("data/{}".format(symbol)).drop(columns = ["Unnamed: 0"])
    analysis = analyze(data, symbol)
    positions = analysis['POSITIONS']
    trade_days = data.index.stop
    total_trade_days = trade_days - 1
    
    required_frequency = total_trade_days * 0.01
    
    if positions >= int(required_frequency):
        return 1
    else:
        return 0

def analyze(data, symbol):
    tech_analysis = technical_analysis(data, data['close'], data['high'], data['low'])

    positions, position = [], 0

    for index in tech_analysis.index:
        if position == 0:
            if tech_analysis.iloc[index]["SIGNAL"] == 1 and\
            tech_analysis.iloc[index]["DI SIGNAL"] == 1 and\
            tech_analysis.iloc[index]["RSI BUY SIGNAL"] == 1 and \
            tech_analysis.iloc[index]["AVERAGE TRUE RANGE"] > 0.1:
                hold = index; position = 1
                continue
        if position == 1:
            if tech_analysis.iloc[index]["close"] > tech_analysis.iloc[hold]['close'] or\
            tech_analysis.iloc[index]["high"] > tech_analysis.iloc[hold]['close'] or\
            tech_analysis.iloc[index]["open"] > tech_analysis.iloc[hold]['close']:
                position = 0; positions.append(index - hold)
    
    holding_time = Counter(positions)
    max_holding_time = holding_time.most_common(1)[0][1]
    
    return {"SYMBOL": "{}".format(symbol), "POSITIONS": len(positions), "MAX_HOLDING_TIME": max_holding_time, "LAST_PRICE": get_yf_quote(symbol)}

def risk_assessment():
    #creting the risk assessment list
    assessment = list()
    
    listing = os.listdir("data")

    with Pool(processes=5) as pool:
        for result in pool.imap_unordered(process, listing):
            if result == None:
                continue
            else:
                assessment.append(result)
    
    data = pd.DataFrame(assessment, columns=["SYMBOL", "POSITIONS", "MAX_HOLDING_TIME", "LAST_PRICE"])
    data['SIGNAL'] = data['SYMBOL'].apply(signal)
    data['POSITION_FREQ'] = data['SYMBOL'].apply(position_freq)

    data = data.sort_values(by=['MAX_HOLDING_TIME']).query("MAX_HOLDING_TIME < 5").sort_values(by=['POSITIONS'], ascending=False).query("SIGNAL == 1").query("POSITION_FREQ == 1").query("LAST_SALE < 5")

    data.to_csv("result.csv") #just for reference

    #data['SPREAD'] = data['SYMBOL'].apply(bid_ask_spread)
    #data = data.query("SPREAD > 0 and SPREAD < 0.5")
    
    symbol = data.head(1).to_dict('records')[0]["SYMBOL"]
    
    if symbol == None:
        logging.info("{}: No Signal Found".format(time.ctime()))
        sys.exit(0)
    
    logging.info("{}: Result is {}".format(today, symbol))
    return symbol


def process(symbol):
    try:
        logging.info("{} : Processing Symbol {}".format(today, symbol))
        historical_data = pd.read_csv("data/{}".format(symbol)).drop(columns = ["Unnamed: 0"])
        return analyze(historical_data, symbol)
    except Exception as e:
        logging.info("{} : Code Exception On Symbol {}: {}".format(time.ctime(), symbol, e))
        return None


def profit_target(open_price, average_true_range):
    #working with 20 percent of the ATR
    atr = correct(average_true_range)
    buy_price = open_price - (0.2 * atr)
    sell_price = buy_price + (0.05 * atr)
    stop_loss = open_price - atr
    return (correct(buy_price), correct(sell_price), correct(stop_loss))

def correct(q):
    return float(Decimal(q).quantize(Decimal('.01'), rounding=ROUND_DOWN))

def get_symbols():
    ftp = FTP('ftp.nasdaqtrader.com')
    ftp.login()
    ftp.cwd('SymbolDirectory')
    
    with open('nasdaqlisted.txt', 'wb') as f:
        ftp.retrbinary('RETR nasdaqlisted.txt', f.write)
    
    ftp.quit()
    
    listing = pd.read_csv('nasdaqlisted.txt', sep = '|')
    symbols = listing['Symbol'].drop(index=listing["Symbol"].tail(1).index.start)
   
    return symbols
            
def quote(symbol):
    header = td.get_access_token()
    data = td.get_quote(symbol, header)
    return data[symbol]['askPrice']

def check_pit_data(t):
    last_day = datetime.date.fromtimestamp(t/1000)
    prev_day = datetime.date.today() - datetime.timedelta(days=1)
    
    if last_day == prev_day:
        return True
    else:
        return False

def get_yf_quote(symbol):
    symbol = yf.Ticker(symbol)
    ask = symbol.info["ask"]
    return ask

def get_yf_volume(symbol):
    symbol = yf.Ticker(symbol)
    volume = symbol.info["volume"]
    return volume

def get_askprice(symbol):
    try:
        header = td.get_access_token()
        symbol_quote = td.get_quote(symbol, header)
        askprice = symbol_quote[symbol]['askPrice']
        time.sleep(1)
        return askprice
    except:
        return 0

def get_atr(symbol):
    try:
        header = td.get_access_token()
        historical_data = td.get_daily_history(symbol, header)
        processed_data = technical_analysis(historical_data, historical_data['close'], historical_data['high'], historical_data['low'])
        atr = processed_data["AVERAGE TRUE RANGE"].tail(1).item()
        time.sleep(2)
        return atr
    except:
        return 0

def get_volume(symbol):
    try:
        header = td.get_access_token()
        historical_data = td.get_daily_history(symbol, header)
        volume = historical_data["volume"].tail(1).item()
        time.sleep(2)
        return volume
    except:
        return 0

def get_places(ask_price):
    return len(str(ask_price).split('.')[1])
