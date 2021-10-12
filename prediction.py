from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, Lasso, Ridge 
from sklearn.exceptions import ConvergenceWarning, EfficiencyWarning, DataDimensionalityWarning
from sklearn.metrics import mean_squared_error

import trade as td
import warnings

import time
import datetime

import logging
import risk_management as rma

warnings.filterwarnings("ignore", category=ConvergenceWarning, module="sklearn")
warnings.filterwarnings("ignore", category=EfficiencyWarning, module="sklearn")
warnings.filterwarnings("ignore", category=DataDimensionalityWarning, module="sklearn")

today = datetime.date.today()

LOG_FILENAME = 'logs/{}-{}-{}.log'.format(today.day, today.month, today.year)
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
)

def process(symbol, target = 'close'):
    try:
        logging.info("Applying Prediction Algorithm to Symbol {}".format(symbol))
        access_token = td.get_access_token()
        data = td.get_history(symbol, access_token)
        analysis = rma.technical_analysis(data, data["close"], data["high"], data["low"])
        
        param_grid = [
                { 'regressor':[LinearRegression()],
                  'preprocessing':[StandardScaler(), MinMaxScaler(), PolynomialFeatures(), None],
                        },
    
                { 'regressor':[Lasso()],
                  'preprocessing':[StandardScaler(), MinMaxScaler(), PolynomialFeatures(), None],
                  'regressor__alpha':[0.001, 0.01, 0.1, 1, 10, 100]
                        },    
                
                { 'regressor':[Ridge()],
                  'preprocessing':[StandardScaler(), MinMaxScaler(), PolynomialFeatures(), None],
                  'regressor__alpha':[0.001, 0.01, 0.1, 1, 10, 100]
                        }
                ]
    
        pipe = Pipeline([('preprocessing', StandardScaler()), ('regressor', LinearRegression())])
        
        analysis[target] = analysis[target].shift(-1)
        analysis = analysis[:-1]
        
        X = analysis.drop(columns=target).to_numpy('float')
        y = analysis[target].to_numpy('float')
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)
    
            
        grid = GridSearchCV(pipe, param_grid, cv=5)
        grid.fit(X_train, y_train)
        
        prediction = grid.predict(X_test)
        mse = mean_squared_error(y_test, prediction)
        
        
        results = [grid.best_params_['regressor'], grid.best_params_['preprocessing']\
                , grid.best_score_, grid.score(X_test, y_test), mse]
        
        data = td.get_history(symbol, access_token)
        analysis = rma.technical_analysis(data, data["close"], data["high"], data["low"])
        
        
        #loading the model
        model = results[0]
    
        #loading the preprocessor
        preprocessor = results[1]
    
        analysis[target] = analysis[target].shift(-1)
        analysis = analysis[:-1]
        
        X = analysis.drop(columns=target).to_numpy('float')
        y = analysis[target].to_numpy('float')
    
        if model == None:
            return 0
        if preprocessor == None:
            y_pred = model.predict(X)
        else:
            y_pred = model.predict(preprocessor.transform(X))
            prediction = y_pred[-1:]
    
        time.sleep(2)
        logging.info("Prediction on Symbol {} Complete".format(symbol))
        
        return prediction[0], results[4], results[3]
    except:
        logging.info("Error occured processing symbol {}".format(symbol))
        return None
    
    
