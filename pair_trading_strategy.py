from __future__ import (absolute_import, division, print_function, unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import numpy as np
import pandas as pd
import backtrader as bt  # Import the backtrader platform
from tabulate import tabulate
import plot_tools, log_tools
import strategys as stg
import quantstats
import pyfolio as pf
import backtrader.feeds as btfeeds
import backtrader.indicators as btind
import indicators as ind
from plot_tools import getBacktestChart

class PairTradingStrategy(bt.Strategy):
    params = (
        ('volumePeriod', 40),
        ('volumeMultiplier', 20),
        ('trendPeriod', 7),
        ('trendMultiplier', 3),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)

    def notify_order(self, order):
        if order.status in [bt.Order.Submitted, bt.Order.Accepted]:
            return  # Await further notifications

        if order.status == order.Completed:
            if order.isbuy():
                buytxt = 'BUY COMPLETE, %.2f' % order.executed.price
                self.log(buytxt, order.executed.dt)
            else:
                selltxt = 'SELL COMPLETE, %.2f' % order.executed.price
                self.log(selltxt, order.executed.dt)

        elif order.status in [order.Expired, order.Canceled, order.Margin]:
            self.log('%s ,' % order.Status[order.status])
            pass  # Simply log

        # Allow new orders
        self.orderid = None

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.startcash = self.broker.getvalue()
        self.heavyTrade = ind.heavyTrade(self.datas[0].volume, period=self.params.volumePeriod, multiplier=self.params.volumeMultiplier/10)
        self.SuperTrend = ind.SuperTrend(self.datas[0], period=self.params.trendPeriod, multiplier=self.params.trendMultiplier)

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('A 收盤價：%.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            invest_value = 0.4 * self.broker.getvalue()  # Divide the cash equally
            x = int(invest_value / (self.data0.close))  # Find the number of shares for Stock1
            y = int(invest_value / (self.data1.close))  # Find the number of shares for Stock2

            # Not yet ... we MIGHT BUY if ...
            if self.heavyTrade[0] == True:
                if self.datas[0].low[0] > self.SuperTrend[0]:
                    # BUY, BUY, BUY!!! (with all possible default parameters)
                    self.buy(data=self.data0, size=x)  # Place an order for buying x + qty1 shares
                    self.sell(data=self.data1, size=y)  # Place an order for selling y + qty2 shares

        else:
            if self.datas[0].high[0] < self.SuperTrend[0]:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                # Keep track of the created order to avoid a 2nd order
                self.close(self.datas[0])
                self.close(self.datas[1])

    def stop(self):
        print('==================================================')
        print('Starting Value - %.2f' % self.broker.startingcash)
        print('Ending   Value - %.2f' % self.broker.getvalue())
        print('==================================================')



if __name__ == '__main__':
    startcash = 1000000
    TWSE_commission = 1.425 / 1000 + 3 / 2000
    full_data = np.load('../datas/個股期標的歷史股價.npy', allow_pickle='TRUE').item()
    final_results_list = []

    # 1101/1102, 2002/2027, 2409/3481/6116, 2498/2388, 2603/2609/2615, 3019/3008/3406, 2915/9945,
    # 2618/2610, 2303/5347/2330, 3037/3189, 8086/3105, 5483/6182/6488, 2881/2882,
    # Prepare data
    stock_id = '2002'
    dataframe = full_data[stock_id]
    dataframe.reset_index(inplace=True)
    dataframe.rename(columns={'Date': 'datetime'}, inplace=True)
    dataframe.drop(['Close'], axis=1)
    dataframe.rename(columns={'Adj Close':'close'}, inplace=True)
    dataframe.set_index('datetime', inplace=True)
    dataframe['openinterest'] = 0
    data = bt.feeds.PandasData(dataname=dataframe, fromdate=datetime.datetime(2010, 1, 1), todate=datetime.datetime(2022, 12, 31))

    stock_id_2 = '2027'
    dataframe_2 = full_data[stock_id_2]
    dataframe_2.reset_index(inplace=True)
    dataframe_2.rename(columns={'Date': 'datetime'}, inplace=True)
    dataframe_2.drop(['Close'], axis=1)
    dataframe_2.rename(columns={'Adj Close':'close'}, inplace=True)
    dataframe_2.set_index('datetime', inplace=True)
    dataframe_2['openinterest'] = 0
    data_2 = bt.feeds.PandasData(dataname=dataframe_2, fromdate=datetime.datetime(2010, 1, 1), todate=datetime.datetime(2022, 12, 31))

    #### normal mode
    # Create a cerebro entity
    cerebro = bt.Cerebro()  # normal mode
    # Add a strategy
    cerebro.addstrategy(PairTradingStrategy)
    # Add the Data Feed to Cerebro
    cerebro.adddata(data)
    cerebro.adddata(data_2)
    # Set our desired cash start
    cerebro.broker.setcash(startcash)
    # Set the commission
    cerebro.broker.setcommission(commission=TWSE_commission)
    # Add trade log
    cerebro.addanalyzer(log_tools.trade_list, _name='trade_list')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='PyFolio')
    # Run
    strats = cerebro.run(tradehistory=True)  # normal mode
    # # get analyzers data, comment out when optimizing
    trade_list = strats[0].analyzers.trade_list.get_analysis()  # normal mode
    print(tabulate(trade_list, headers="keys"))  # normal mode
    # quantstats
    portfolio_stats = strats[0].analyzers.getbyname('PyFolio')
    returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
    returns.index = returns.index.tz_convert(None)
    file_name = stock_id +'_' + stock_id_2 + '_Stats.html'
    quantstats.reports.html(returns, download_filename=file_name, output='yes', title= stock_id + 'vs.' + stock_id_2 +' 績效表')

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue()) # normal mode

    # Plot the result
    # cerebro.plot(iplot=False)  # using 'iplot=False' to avoid error message

    figure=cerebro.plot(style = 'candlebars')[0][0]
    figure[0][0].savefig(f'data/cerebro_{sector}_{direction[0]}_{style[0]}_{date_cur}.png')