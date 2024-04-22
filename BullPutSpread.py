import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt
import scipy.stats as sps
from nelson_siegel_svensson.calibrate import calibrate_nss_ols

############################
# Options helper functions #
############################

def call_delta(S, K, r, T, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return sps.norm.cdf(d1)

def put_delta(S, K, r, T, sigma):
    return call_delta(S, K, r, T, sigma) - 1

def short_call_delta(S, K, r, T, sigma):
    return -call_delta(S, K, r, T, sigma)

def short_put_delta(S, K, r, T, sigma):
    return -put_delta(S, K, r, T, sigma)

def compute_smile(r: np.array, T: float, S0: float, K: np.array, price: np.array, initial_guess: float = 0.3, smooth: bool = False):

    # source : https://www.quora.com/What-is-the-best-practically-method-to-calculate-implied-volatility

    assert len(K) == len(price)
    smile = np.zeros(len(K))

    atm_index = np.argmin(np.abs(K - S0))
    
    def halley_method_put(sigma_init, r, T, S0, K, market_price, max_iter=100, tol=1e-6):
        sigma = sigma_init
        for i in range(max_iter):
            d1 = (np.log(S0/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
            d2 = d1 - sigma*np.sqrt(T)
            vega = S0*np.sqrt(T)*sps.norm.pdf(d1)
            price = K*np.exp(-r*T)*sps.norm.cdf(-d2) - S0*sps.norm.cdf(-d1)
            diff = price - market_price
            if abs(diff) < tol:
                return sigma
            if vega < 1e-10:
                return sigma
            
            sigma = max(sigma - ((2*(price - market_price)) / (2*vega - (price - market_price)*d1*d2/sigma)), 1e-4)

            """if sigma <= 1e-4:
                return sigma_init"""
        print("Halley method did not converge")
        return sigma_init
    
    atm_iv = halley_method_put(initial_guess, r[atm_index], T, S0, K[atm_index], price[atm_index])
    smile[atm_index] = atm_iv

    for i in range(atm_index+1, len(K)):
        smile[i] = halley_method_put(smile[i-1], r[i], T, S0, K[i], price[i])
    for i in range(atm_index-1, -1, -1):
        smile[i] = halley_method_put(smile[i+1], r[i], T, S0, K[i], price[i])

    # smooth the smile with a 3rd degree polynomial
    if smooth:
        poly = np.poly1d(np.polyfit(K, smile, 5))
        smile = poly(K)

    return smile

############################
# Bull Put Spread Strategy #
############################

class BullPutSpread:
    def __init__(self, ticker) -> None:
        yields_maurities = np.array([1/12, 2/12, 3/12, 4/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30])
        yields = np.array([5.49, 5.52, 5.46, 5.44, 5.39, 5.18, 4.98, 4.83, 4.68, 4.67, 4.64, 4.85, 4.74]).astype(float)/100
        curve_fit, status = calibrate_nss_ols(yields_maurities , yields)
        #spy_calls["rate"] = spy_calls["maturity"].apply(lambda x: curve_fit(x))
        self.ticker = ticker
        now = datetime.now()
        one_year_ago = datetime(now.year - 1, now.month, now.day)
        self.stock = yf.download(ticker, start=one_year_ago, end=now)
        self.stock['log_returns'] = np.log(self.stock['Close'] / self.stock['Close'].shift(1))
        now = self.stock.index[-1]
        self.maturities = yf.Ticker(ticker).options
        print(self.maturities)
        self.puts = pd.DataFrame()
        for maturity in self.maturities:
            new_puts = yf.Ticker(ticker).option_chain(maturity).puts
            new_puts['maturity'] = maturity
            new_puts['days_to_maturity'] = (pd.to_datetime(maturity) - now).days
            new_puts['rate'] = curve_fit(new_puts['days_to_maturity'].values/252.0)
            new_puts['IV'] = compute_smile(new_puts['rate'].values, new_puts['days_to_maturity'].values[0]/252.0, self.stock['Close'].iloc[-1], new_puts['strike'].values, (new_puts['ask'].values + new_puts['bid'].values)/2.0, smooth=False)
            new_puts['delta'] = [put_delta(self.stock['Close'].iloc[-1], K, r, T, IV) for K, r, T, IV in zip(new_puts['strike'].values, new_puts['rate'].values, new_puts['days_to_maturity'].values/252.0, new_puts['IV'].values)]
            self.puts = pd.concat([self.puts, new_puts])
        self.puts = self.puts.reset_index()
        self.maturities = self.puts['maturity'].unique()

        self.underlying_price = self.stock['Close'].iloc[-1]

        self.strategy = {
            'short_put': {
                'strike': None,
                'maturity': None,
                'price': None
            },
            'long_put': {
                'strike': None,
                'maturity': None,
                'price': None
            }
        }
        
    def get_maturities(self) -> list:
        return self.maturities
    
    def get_strikes(self, maturity: str) -> list:
        return self.puts.loc[self.puts['maturity'] == maturity]['strike'].tolist()
    
    def set_short_put(self, strike: float, maturity: str) -> None:
        self.strategy['short_put']['strike'] = strike
        self.strategy['short_put']['maturity'] = maturity
        self.strategy['short_put']['price'] = self.puts.loc[(self.puts['strike'] == strike) & (self.puts['maturity'] == maturity)]['bid'].values[0]

    def set_long_put(self, strike: float, maturity: str) -> None:
        self.strategy['long_put']['strike'] = strike
        self.strategy['long_put']['maturity'] = maturity
        self.strategy['long_put']['price'] = self.puts.loc[(self.puts['strike'] == strike) & (self.puts['maturity'] == maturity)]['ask'].values[0]

    def get_max_profit(self) -> float:
        return 100*(self.strategy['short_put']['price'] - self.strategy['long_put']['price'])
    
    def get_max_loss(self) -> float:
        return 100*(self.strategy['long_put']['strike'] - self.strategy['short_put']['strike']) + self.get_max_profit()
    
    def get_breakeven(self) -> float:
        return self.strategy['short_put']['strike'] - self.get_max_profit()/100.0
    
    def get_payoff(self, underlying_price: float) -> float:
        if underlying_price > self.strategy['short_put']['strike']:
            return self.get_max_profit()
        elif underlying_price < self.strategy['long_put']['strike']:
            return self.get_max_loss()
        else:
            return self.get_max_profit() + (underlying_price - self.strategy['short_put']['strike'])*100
        
    def get_delta(self, type: str) -> float:
        # delta of the a long put using the formula : dP/dS = (P - dP/dK) / S
        if type == 'long_put':
            maturity = self.strategy['long_put']['maturity']
            T = self.puts.loc[self.puts['maturity'] == maturity]['days_to_maturity'].values[0]/252.0
            K = self.strategy['long_put']['strike']
            S = self.underlying_price
            r = self.puts.loc[(self.puts['strike'] == K) & (self.puts['maturity'] == maturity)]['rate'].values[0]
            IV = self.puts.loc[(self.puts['strike'] == K) & (self.puts['maturity'] == maturity)]['IV'].values[0]
            return put_delta(S, K, r, T, IV)
        
        elif type == 'short_put':
            maturity = self.strategy['short_put']['maturity']
            T = self.puts.loc[self.puts['maturity'] == maturity]['days_to_maturity'].values[0]/252.0
            K = self.strategy['short_put']['strike']
            S = self.underlying_price
            r = self.puts.loc[(self.puts['strike'] == K) & (self.puts['maturity'] == maturity)]['rate'].values[0]
            IV = self.puts.loc[(self.puts['strike'] == K) & (self.puts['maturity'] == maturity)]['IV'].values[0]
            return short_put_delta(S, K, r, T, IV)

        else:
            raise ValueError('Invalid option type')

    def plot_payoff(self, save_figure_to: str = None) -> None:
        short_strike = self.strategy['short_put']['strike']
        long_strike = self.strategy['long_put']['strike']

        d = np.abs(short_strike - long_strike)
        x = np.linspace(0.95*long_strike, 1.05*short_strike, 100)
        y = [self.get_payoff(i) for i in x]

        plt.plot(x, y, label='Payoff')
        plt.axhline(0, color='black', linestyle='--')
        plt.axvline(short_strike, color='red', linestyle='--')
        plt.axvline(long_strike, color='red', linestyle='--')
        plt.axvline(self.get_breakeven(), color='green', linestyle='--', label=f'Breakeven ({round(self.get_breakeven(), 2)})')
        plt.xlabel('Underlying Price')
        plt.ylabel('Payoff')
        plt.title(f'{self.ticker} Bull Put Spread Payoff (Max Profit: {round(self.get_max_profit(), 2)}, Max Loss: {round(self.get_max_loss(), 2)})')
        plt.legend()

        if save_figure_to is not None:
            plt.savefig(save_figure_to)

        plt.show()
        
    def plot_iv(self, maturity):
        plt.plot(self.puts.loc[self.puts['maturity'] == maturity]['strike'], self.puts.loc[self.puts['maturity'] == maturity]['IV'])
        plt.grid()
        plt.xlabel('Strike')
        plt.ylabel('Implied Volatility')
        plt.title(f'{self.ticker} Puts Implied Volatility Smile ({maturity})')
        plt.show()

    def plot_delta(self, maturity) -> None:
        plt.plot(self.puts.loc[self.puts['maturity'] == maturity]['strike'], self.puts.loc[self.puts['maturity'] == maturity]['delta'])
        plt.axvline(self.underlying_price, color='red', linestyle='--', label='ATM')
        plt.grid()
        plt.xlabel('Strike')
        plt.ylabel('Delta')
        plt.title(f'{self.ticker} Puts Delta Smile ({maturity})')
        plt.show()