import yfinance as yf
import matplotlib.pyplot as plt
import numpy as npf
import pandas as pd
import datetime 
from datetime import date, datetime, timedelta, timezone
from smart_weights import *

# Variables
# Will have to globalize the yfinance data too cause having to constantly do api calls is going to make our code really slow
global stock 
global stock_info


# two step process
# 1. Input a ticker
# 2. Then the user will input the function 


def last_trading_day():
    now = datetime.now(timezone(timedelta(hours=-5), 'EST'))

    # US Markets close at 4pm, but afterhours trading ends at 8pm.
    # yFinance stubbornly only gives the day's data after 8pm, so we will wait until 9pm to pull data from
    # the current day.
    market_close = now.replace(hour=21, minute=0, second=0, microsecond=0)
    if now < market_close:
        DELTA = 1
    # If it is saturday or sunday
    elif now.weekday() >= 5:
        DELTA = 1
    else:
        DELTA = 0
        
    start_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
    end_date = (datetime.now() - pd.tseries.offsets.BDay(DELTA)).strftime("%Y-%m-%d")
    MarketIndex = "^GSPC" # We can use the S&P 500's data to see the last day where we have data

    market_hist = yf.Ticker(MarketIndex).history(start=start_date, end=end_date).filter(like="Close").dropna()   

    latest_day = market_hist.index[-1]
    return latest_day.strftime("%Y-%m-%d")


# Stock Info (Open, High, Low, Close, Volume, Dividends, Stock Splits)  
def stock_info(ticker):    
    stock_infopkg = {}
    beta_std = betastd(ticker)
    stock_infopkg['Beta'] = f'{beta_std[0]:.2f}'
    stock_infopkg['STD'] = f'{beta_std[1]:.2f}'
    stock_infopkg['52Wk High'] = f'{beta_std[2][ticker].High.max():.2f}'
    stock_infopkg['52Wk Low'] = f'{beta_std[2][ticker].Low.min():.2f}'
    stock_infopkg['Last Trading Day Open'] = f'{beta_std[2][ticker].Open[-1]:.2f}'
    stock_infopkg['Last Trading Day Close'] = f'{beta_std[2][ticker].Close[-1]:.2f}'

    return stock_infopkg


# PyZipFile Class for creating ZIP archives containing Python libraries.     class zipfile.ZipInfo(filename='NoName', date_time=, 1980, 1, 1, 0, 0, 0)
# Stock History 

def valid_ticker_list(ticker_list):
    ticker_hist = yf.download(
                    tickers = " ".join(ticker_list),
                    # Download Data From the past 6 months
                    period = "5d",
                    interval = "1d",
                    group_by = 'tickers',
                    threads = True
                )
    return list(dict.fromkeys([t[0] for t in ticker_hist.dropna(axis=1, how='all').columns]))

def create_price_list(ticker_list):
    new_ticker_list = sorted(ticker_list)
    price_list = []
    ticker_hist = yf.download(
                    tickers = " ".join(ticker_list),
                    # Download Data From the past 6 months
                    period = "5d",
                    interval = "1d",
                    threads = True
                )
    last_row = ticker_hist['Close'].iloc[-1]
    last_date = (ticker_hist.iloc[-1].name).strftime("%Y-%m-%d")
    for x in new_ticker_list:
        price_list.append(last_row[x])
    return (price_list, last_date)

class Portfolio:
    
    def __init__(self, ticker_list, start_date, end_date, starting_balance):
        self.set_start_date(start_date)
        self.set_end_date(end_date)
        self.set_ticker_list(ticker_list)
        self.starting_balance = starting_balance

    # Setters
    def set_ticker_list(self, ticker_list):
        self.ticker_list = ticker_list

    def set_start_date(self, start_date):
        self.start_date = start_date
    
    def set_end_date(self, end_date):
        self.end_date = end_date

    def set_starting_balance(self, starting_balance):
        self.starting_balance = starting_balance
    

    # Getters
    #def get_ticker_list(self):
       # return self.__ticker_list

    #def add_ticker(self, ticker):
    #    ticker_list.append(ticker)

    # Functions

    def add_ticker(self, ticker):
        self.ticker_list.append(ticker)


def stock_history(ticker, start_date, end_date):
    current_date = date.today()
    stock = yf.Ticker(ticker)
    if start_date == "" or end_date == "":
        stock_history = stock.history(start = date.today, end = date.today) 
    else:
        stock_history = stock.history(start = start_date, end = end_date) 
    return stock_history


def price_weighted(ticker_list, starting_balance, price_list):

    # Create DataFrame
    pw_portfolio = pd.DataFrame(index = ticker_list)
    pw_portfolio["Shares"] = 0
    num_tickers = len(ticker_list)
    value_per_share = starting_balance/num_tickers
    
    # Add Close price columns for each stock
    
    for i in range(len(ticker_list)):
        
        pw_portfolio['Shares'].loc[ticker_list[i]] = value_per_share/price_list[i]
    

    return pw_portfolio


def market_weighted(ticker_list, starting_balance, price_list):
    
    stock_dict = {}
    totalMarketCap = 0
    for i in range(len(ticker_list)):
        stock_dict[f"{ticker_list[i]} Shares Outstanding"] = yf.Ticker(ticker_list[i]).info["sharesOutstanding"]
        stock_dict[f"{ticker_list[i]} Market Capitalization"] = stock_dict[f"{ticker_list[i]} Shares Outstanding"] * price_list[i]
        totalMarketCap += stock_dict[f"{ticker_list[i]} Market Capitalization"]
    
    market_weighted_df = pd.DataFrame(index = ticker_list)
    market_weighted_df.index.rename("Ticker", inplace = True)
    market_weighted_df["Shares"] = 0
    
    for i in range(len(ticker_list)):
        stock_dict[f"{ticker_list[i]} Market Capitalization Percent"] = stock_dict[f"{ticker_list[i]} Market Capitalization"] / totalMarketCap
        market_weighted_df.loc[ticker_list[i],"Shares"] = (stock_dict[f"{ticker_list[i]} Market Capitalization Percent"] * starting_balance) / price_list[i]
   
    return market_weighted_df

    
def portfolio_maker(ticker_list, weight_option, starting_balance):
    
    # Get valid ticker list
    valid_tickers = valid_ticker_list(ticker_list)
    tot_data = create_price_list(valid_tickers)
    prices_list = tot_data[0]
    last_day = tot_data[1]
    if not valid_tickers:
        print('No valid tickers were inputted!')
        return None
    elif len(valid_tickers) > 10:
        print('Exceeded Maximum Number of Tickers!')
        return None
    else:
        # check weight option
        if weight_option == 'PRICE WEIGHTED':
            portfolio = price_weighted(ticker_list,starting_balance,prices_list)

        elif weight_option == 'MARKET WEIGHTED':
            portfolio = market_weighted(ticker_list,starting_balance,prices_list)

        else:
            portfolio = smart_weighted(ticker_list, weight_option)
        
        if not portfolio:
            return None
        else:
            pass
        return (portfolio,last_day)



# Earnings per Share/ Return on equity?


# Company info (location, industry, market capitalization)
def company_info(ticker):
    try:
        location = ticker.info['city'] + ", " + ticker.info['country']
        industry = ticker.info['industry']
        market_cap = ticker.info['marketCap']
        return [location, industry, market_cap]
    except: 
        print("Oops! There's no information available!")
    

def regenerate_portfolio(portfolio: dict):
    last_tday = last_trading_day()
    incep_dates = []
    
    # Create a list of dates to find the earliest date
    for ticker in portfolio:
        incep_dates.append(portfolio[ticker][1])
    
    # Find the smallest date (earliest)
    earliest_date = sorted(incep_dates)[0]
    
    # Download Stock Data
    pricing_data = yf.download(
        tickers = " ".join(ticker for ticker in portfolio),
        start=earliest_date,
        end=last_tday,
        interval = '1d',
        group_by='ticker',
        threads=True  
    )
    portfolio_df = pd.DataFrame()
    portfolio_df["Dates"] = pd.date_range(start=earliest_date, end=last_tday, freq="B")
    portfolio_df.set_index("Dates", inplace = True)
    
    # Find total investment (the amount of money put in)
    investment = 0
    for ticker in portfolio:
        investment += pricing_data[ticker].loc[portfolio[ticker][1]] * portfolio[ticker][0]
        
    for ticker in portfolio:
        portfolio_df[f'{ticker}_SHARES'] = 0
        portfolio_df[f'{ticker}_SHARES'].loc[portfolio[ticker][1]:] += float(portfolio[ticker][0])
        portfolio_df[f'{ticker}_CLOSE'] = pricing_data[ticker].Close
        portfolio_df[f'{ticker}_VALUE'] = portfolio_df[f'{ticker}_SHARES'] * portfolio_df[f'{ticker}_CLOSE']  
    
    portfolio_df.dropna(how='all', inplace=True)
    portfolio_df['TOTAL_VALUE'] = portfolio_df.filter(like='_VALUE').sum(axis=1)
    portfolio_df = portfolio_df[['TOTAL_VALUE']].loc[(portfolio_df[['TOTAL_VALUE']]!=0).any(axis=1)]
    portfolio_df['RETURNS'] = portfolio_df['TOTAL_VALUE'].pct_change() * 100
    return (portfolio_df[['TOTAL_VALUE', 'RETURNS']], investment)

    
    
    
        
        


# {'HOOD': [Decimal('1.12345'), '2021-21-24'],
# ,
# ,
# ,
# ,
# ,
# }
# print(get_portfolio(00000))

def portfolio_graphs(portfolio: dict, userid: int):
    # Create desired portfolio with ticker list
    data = regenerate_portfolio(portfolio)
    portfolio_df = data[0]
    initial_investment = data[1]
    print(portfolio_df)

    # Initiate plot

    plt.suptitle(f'Daily Portfolio Returns: {portfolio_df.index[0].strftime("%Y-%m-%d")} to {portfolio_df.index[-1].strftime("%Y-%m-%d")}')

    plt.plot(portfolio_df.index, portfolio_df['TOTAL_VALUE'])
    plt.xlabel('Dates')
    plt.ylabel('Value ($)')

    # Create png of graphs
    plt.savefig(f'process/{userid}.png')
    return (initial_investment, portfolio_df['TOTAL_VALUE'][-1])



# Beta Value       
def betastd(ticker):
    stock = yf.Ticker(ticker)
    market = yf.Ticker('^GSPC')
    
    ticker_hist = yf.download(
                    tickers = " ".join([ticker, '^GSPC']),
                    # Download Data From the past 6 months
                    period = "12mo",
                    interval = "1d",
                    group_by = 'tickers',
                    threads = True
                )
    prices = pd.DataFrame(ticker_hist[ticker].Close)
    prices.columns = [ticker]
    prices['^GSPC'] = ticker_hist['^GSPC'].Close
    # Calculate monthly returns
    monthly_returns = prices.resample('M').ffill().pct_change()
    monthly_returns.drop(index=monthly_returns.index[0], inplace=True)
    # Calculate the market variance
    MarketVar = monthly_returns['^GSPC'].var()
    Beta=monthly_returns.cov()/MarketVar
    return (Beta.iat[0,1], monthly_returns[ticker].std(), ticker_hist)


# Sharpe Ratio
def sharpe_ratio(ticker, start_date, end_date):
    # For sharpe ratio we need a portfolio so for simplicity I will just let the portfolio just be 1 share of whatever we are interested in
    price_history = stock_history(ticker, start_date, end_date)

    sharpe_ratio = price_history['Close'].pct_change().mean() / price_history['Close'].pct_change().std()

    #Will have to double check if this actually works or not
    return sharpe_ratio
    
def pe_ratio(ticker_list):

    # Get valid ticker list
    valid_tickers = valid_ticker_list(ticker_list)

    if not valid_tickers:
        print('No valid tickers were inputted!')
    elif len(valid_tickers) > 10:
        print('Exceeded Maximum Number of Tickers!')
    else:
        share_price_sum = 0
        earnings_sum = 0

        for i in range(len(ticker_list)):
            ticker = yf.Ticker(ticker_list[i])
            ticker_info = ticker.info
            share_price_sum += ticker_info['currentPrice']
            earnings_sum += (ticker_info['grossProfits']/ticker_info['sharesOutstanding'])
    
    return share_price_sum/earnings_sum

# Options
#Requires the user to input a price range and put/call 
def options(ticker, range_length, put_call):
    stock = yf.Ticker(ticker)
    opt = stock.option_chain(stock.options[1])
    
    #If user wants put option or call option
    if put_call == "put":
        opt = pd.DataFrame().append(opt.puts)
    elif put_call == "call":
        opt = pd.DataFrame().append(opt.calls)

    stockSP = stock.info['currentPrice']

    #Determine and display the calls that meet the criteria that is $5 within the current price
    calls = opt.loc[((stockSP-range_length)<=opt['strike'])&((stockSP+range_length) >= opt['strike'])]

    return calls


#Volatility (standard deviation)
def std(portfolio):

    monthly_returns = portfolio.resample('MS').first().pct_change()

    return monthly_returns.std() 


#Correlation with other stocks (need 2 tickers to be inputed)
def correlation(ticker1, ticker2):
    # get ticker info
    ticker1 = yf.Ticker(ticker1)
    ticker1_info = ticker1.info
    
    ticker2 = yf.Ticker(ticker2)
    ticker2_info = ticker2.info
    
    # check ticker validity, and proceeding  
    if ticker1_info['regularMarketPrice'] != None or ticker2_info['regularMarketPrice'] != None:
        from datetime import datetime
        start_date = '1900-01-01'
        now = datetime.now()
        end_date = now.strftime("%Y-%m-%d")
        un_ticker1_hist = ticker1.history(start = start_date, close = end_date)
        un_ticker2_hist = ticker2.history(start = start_date, close = end_date)
        if un_ticker1_hist.index[0].strftime("%Y-%m-%d") > un_ticker2_hist.index[0].strftime("%Y-%m-%d"):
            real_start_date = un_ticker2_hist.index[0].strftime("%Y-%m-%d")
        else:
            real_start_date = un_ticker1_hist.index[0].strftime("%Y-%m-%d")
        ticker1_hist = ticker1.history(start = real_start_date, close = end_date ,interval="1mo").dropna()
        ticker2_hist = ticker2.history(start = real_start_date, close = end_date, interval = "1mo").dropna()
        prices = pd.DataFrame(ticker1_hist['Close'])
        prices.columns = [ticker1]
        prices[ticker2] = ticker2_hist['Close']
        monthly_returns = 100 * prices.pct_change()[1:]
        print("Correlation:")
        print(100 * monthly_returns.corr().iat[0,1])

    else:
        print("Invalid Ticker(s). Please try again.")

# Different companies and fees