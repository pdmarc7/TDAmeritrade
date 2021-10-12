import datetime
import ta
import logging

today = datetime.date.today()

LOG_FILENAME = 'logs/{}-{}-{}.log'.format(today.day, today.month, today.year)
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
)


###############################################################################
    
                        #SUPPORTING FUNCTIONS

###############################################################################
def technical_analysis(ndata, close, high, low):
    #copy data
    data = ndata.copy()
    #OSCILLATORS
    rsi = ta.momentum.RSIIndicator(close, n = 14, fillna = True)
    stochastic = ta.momentum.StochasticOscillator(high, low, close, n = 14, d_n = 3, fillna = True)
    #RELATIVE STRENGTH INDEX
    data['RSI'] = rsi.rsi()
    #STOCHASTICS
    data['STOCHASTIC %K LINE'] = stochastic.stoch()
    data['STOCHASTIC %D LINE'] = stochastic.stoch_signal()
    #BUY-SIGNAL
    data["BUY-SIGNAL"] = (data["STOCHASTIC %D LINE"] < 20) & (data["RSI"] < 50)
    #SELL-SIGNAL
    data["SELL-SIGNAL"] = (data["RSI"] > 70) & (data["STOCHASTIC %D LINE"] > 80)
    return data
