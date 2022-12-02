from __future__ import (absolute_import, division, print_function, unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import backtrader as bt  # Import the backtrader platform
from tabulate import tabulate
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
# import pyfolio as pf

def my_heatmap(data):
    data = np.array(data)
    xs = np.unique(data[:, 1].astype(int))
    ys = np.unique(data[:, 0].astype(int))
    vals = data[:, 2].reshape(len(ys), len(xs))
    min_val_ndx = np.unravel_index(np.argmin(vals, axis=None), vals.shape)
    max_val_ndx = np.unravel_index(np.argmax(vals, axis=None), vals.shape)

    cmap = LinearSegmentedColormap.from_list('', ['red', 'orange', 'yellow', 'chartreuse', 'limegreen'])
    ax = sns.heatmap(vals, xticklabels=xs, yticklabels=ys, cmap=cmap, annot=True, fmt='.2f')

    ax.add_patch(Rectangle(min_val_ndx[::-1], 1, 1, fill=False, edgecolor='blue', lw=3, clip_on=False))
    ax.add_patch(Rectangle(max_val_ndx[::-1], 1, 1, fill=False, edgecolor='blue', lw=3, clip_on=False))

    plt.tight_layout()
    plt.show()

# Trade list similar to Amibroker output
class trade_list(bt.Analyzer):

    def get_analysis(self):

        return self.trades


    def __init__(self):

        self.trades = []
        self.cumprofit = 0.0

    def notify_trade(self, trade):

        if trade.isclosed:

            brokervalue = self.strategy.broker.getvalue()

            dir = 'short'
            if trade.history[0].event.size > 0: dir = 'long'

            pricein = trade.history[len(trade.history)-1].status.price
            priceout = trade.history[len(trade.history)-1].event.price
            datein = bt.num2date(trade.history[0].status.dt)
            dateout = bt.num2date(trade.history[len(trade.history)-1].status.dt)
            if trade.data._timeframe >= bt.TimeFrame.Days:
                datein = datein.date()
                dateout = dateout.date()

            pcntchange = 100 * priceout / pricein - 100
            pnl = trade.history[len(trade.history)-1].status.pnlcomm
            pnlpcnt = 100 * pnl / brokervalue
            barlen = trade.history[len(trade.history)-1].status.barlen
            pbar = pnl / barlen
            self.cumprofit += pnl

            size = value = 0.0
            for record in trade.history:
                if abs(size) < abs(record.status.size):
                    size = record.status.size
                    value = record.status.value

            highest_in_trade = max(trade.data.high.get(ago=0, size=barlen+1))
            lowest_in_trade = min(trade.data.low.get(ago=0, size=barlen+1))
            hp = 100 * (highest_in_trade - pricein) / pricein
            lp = 100 * (lowest_in_trade - pricein) / pricein
            if dir == 'long':
                mfe = hp
                mae = lp
            if dir == 'short':
                mfe = -lp
                mae = -hp

            self.trades.append({'ref': trade.ref, 'ticker': trade.data._name, 'dir': dir,
                 'datein': datein, 'pricein': pricein, 'dateout': dateout, 'priceout': priceout,
                 'chng%': round(pcntchange, 2), 'pnl': pnl, 'pnl%': round(pnlpcnt, 2),
                 'size': size, 'value': value, 'cumpnl': self.cumprofit,
                 'nbars': barlen, 'pnl/bar': round(pbar, 2),
                 'mfe%': round(mfe, 2), 'mae%': round(mae, 2)})

            """
            Outputs -
            ref - bt's unique trade identifier
            ticker - data feed name
            datein - date and time of trade opening
            pricein - price of trade entry
            dir - long or short
            dateout - date and time of trade closing
            priceout - price of trade exit
            chng% - exit price to entry price ratio
            pnl - money profit/loss per trade
            pnl% - proft/loss in %s to broker's value at the trade closing
            cumpnl - cumulative profit/loss
            size - max position size during trade
            value - max trade value
            nbars - trade duration in bars
            pnl/bar - profit/loss per bar
            mfe% - max favorable excursion
            mae% - max adverse excursion
            """


class heavyTrade(bt.Indicator):
    lines = ('heavyTrade',)
    params = (('period', 30),('multiplier',1.5))
    # plotinfo = dict(subplot=False)

    def __init__(self):
        self.lines.heavyTrade = self.data > self.p.multiplier * bt.ind.MaxN(self.data(-1), period=self.p.period)


class SuperTrendBand(bt.Indicator):
    """
    Helper inidcator for Supertrend indicator
    """
    params = (('period',7),('multiplier',3))
    lines = ('basic_ub','basic_lb','final_ub','final_lb')


    def __init__(self):
        self.atr = bt.indicators.AverageTrueRange(period=self.p.period)
        self.l.basic_ub = ((self.data.high + self.data.low) / 2) + (self.atr * self.p.multiplier)
        self.l.basic_lb = ((self.data.high + self.data.low) / 2) - (self.atr * self.p.multiplier)

    def next(self):
        if len(self)-1 == self.p.period:
            self.l.final_ub[0] = self.l.basic_ub[0]
            self.l.final_lb[0] = self.l.basic_lb[0]
        else:
            #=IF(OR(basic_ub<final_ub*,close*>final_ub*),basic_ub,final_ub*)
            if self.l.basic_ub[0] < self.l.final_ub[-1] or self.data.close[-1] > self.l.final_ub[-1]:
                self.l.final_ub[0] = self.l.basic_ub[0]
            else:
                self.l.final_ub[0] = self.l.final_ub[-1]

            #=IF(OR(baisc_lb > final_lb *, close * < final_lb *), basic_lb *, final_lb *)
            if self.l.basic_lb[0] > self.l.final_lb[-1] or self.data.close[-1] < self.l.final_lb[-1]:
                self.l.final_lb[0] = self.l.basic_lb[0]
            else:
                self.l.final_lb[0] = self.l.final_lb[-1]

class SuperTrend(bt.Indicator):
    """
    Super Trend indicator
    """
    params = (('period', 7), ('multiplier', 2))
    lines = ('super_trend',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.stb = SuperTrendBand(period = self.p.period, multiplier = self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.super_trend[0] = self.stb.final_ub[0]
            return

        if self.l.super_trend[-1] == self.stb.final_ub[-1]:
            if self.data.close[0] <= self.stb.final_ub[0]:
                self.l.super_trend[0] = self.stb.final_ub[0]
            else:
                self.l.super_trend[0] = self.stb.final_lb[0]

        if self.l.super_trend[-1] == self.stb.final_lb[-1]:
            if self.data.close[0] >= self.stb.final_lb[0]:
                self.l.super_trend[0] = self.stb.final_lb[0]
            else:
                self.l.super_trend[0] = self.stb.final_ub[0]


# Create a Stratey
class TrendFollowStrategy(bt.Strategy):
    params = (
        ('volumePeriod', 40),
        ('volumeMultiplier', 20),
        ('trendPeriod', 7),
        ('trendMultiplier', 3),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.startcash = self.broker.getvalue()
        self.heavyTrade = heavyTrade(self.datas[0].volume, period=self.params.volumePeriod, multiplier=self.params.volumeMultiplier/10)
        self.SuperTrend = SuperTrend(self.datas[0], period=self.params.trendPeriod, multiplier=self.params.trendMultiplier)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f, cash %.2f' %
                    (order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm,
                     self.broker.get_cash()))

            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f, cash %.2f' %
                         (order.executed.price,
                          order.executed.size,
                          order.executed.value,
                          order.executed.comm,
                        self.broker.get_cash()))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('A 收盤價：%.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Not yet ... we MIGHT BUY if ...
            if self.heavyTrade[0] == True:
                if self.datas[0].low[0] > self.SuperTrend[0]:
                    # BUY, BUY, BUY!!! (with all possible default parameters)
                    self.order = self.buy(self.datas[0])

        else:
            if self.datas[0].high[0] < self.SuperTrend[0]:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                # Keep track of the created order to avoid a 2nd order
                self.order = self.close(self.datas[0])

    # def stop(self):
    #     pnl = round(self.broker.getvalue() - self.startcash,2)
    #     print('Volume Period: {} Volume Multiplier: {} Final PnL: {}'.format(
    #         self.params.volumePeriod, self.params.volumeMultiplier, pnl))

if __name__ == '__main__':

    # Prepare data
    full_data = np.load('../datas/個股期標的歷史股價.npy', allow_pickle='TRUE').item()
    dataframe = full_data['1101']
    dataframe.reset_index(inplace=True)
    dataframe.rename(columns={'Date': 'datetime'}, inplace=True)
    dataframe.drop(['Close'],axis=1)
    dataframe.rename(columns={'Adj Close':'close'}, inplace=True)
    dataframe.set_index('datetime', inplace=True)
    dataframe['openinterest'] = 0
    data = bt.feeds.PandasData(dataname=dataframe, fromdate=datetime.datetime(2010, 1, 1), todate=datetime.datetime(2022, 12, 31))

    startcash = 2000000

    # #### normal mode
    # # Create a cerebro entity
    # cerebro = bt.Cerebro()  # normal mode
    # # Add a strategy
    # cerebro.addstrategy(TrendFollowStrategy)
    # # Add the Data Feed to Cerebro
    # cerebro.adddata(data)
    # # Set our desired cash start
    # cerebro.broker.setcash(startcash)
    # # Add a FixedSize sizer according to the stake
    # cerebro.addsizer(bt.sizers.FixedSize, stake=1000)
    # # Set the commission
    # TWSE_commission = 1.425/1000 + 3/2000
    # cerebro.broker.setcommission(commission=TWSE_commission)
    # # Add trade log
    # cerebro.addanalyzer(trade_list, _name='trade_list')
    # # Run
    # strats = cerebro.run(tradehistory=True)  # normal mode
    # # get analyzers data, comment out when optimizing
    # trade_list = strats[0].analyzers.trade_list.get_analysis()  # normal mode
    # print(tabulate(trade_list, headers="keys"))  # normal mode
    # # Print out the final result
    # print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue()) # normal mode
    #
    # # Plot the result
    # cerebro.plot(iplot=False)  # using 'iplot=False' to avoid error message

    ####
    ####
    ####
    # #### optimize mode
    # cerebro = bt.Cerebro(optreturn=False)  # optimize mode
    # # Add a strategy
    # cerebro.optstrategy(TrendFollowStrategy, volumePeriod = range(30, 50), volumeMultiplier = range(10, 30))
    # # cerebro.optstrategy(TrendFollowStrategy, volumePeriod = range(30, 33), volumeMultiplier = range(10, 15))
    # # Add the Data Feed to Cerebro
    # cerebro.adddata(data)
    # # Set our desired cash start
    # cerebro.broker.setcash(startcash)
    # # Add a FixedSize sizer according to the stake
    # cerebro.addsizer(bt.sizers.FixedSize, stake=1000)
    # # Set the commission
    # TWSE_commission = 1.425/1000 + 3/2000
    # cerebro.broker.setcommission(commission=TWSE_commission)
    # # Run
    # opt_runs = cerebro.run(tradehistory=True)  # optimize mode
    #
    # # Generate results list
    # final_results_list = []
    # for run in opt_runs:
    #     for strategy in run:
    #         value = round(strategy.broker.get_value(),2)
    #         PnL = round(value - startcash,2)
    #         period = strategy.params.volumePeriod
    #         multiplier = strategy.params.volumeMultiplier
    #         final_results_list.append([period, multiplier, PnL])
    #
    # #Sort Results List
    # by_period = sorted(final_results_list, key=lambda x: x[0])
    # by_PnL = sorted(final_results_list, key=lambda x: x[1], reverse=True)
    #
    # #Print results
    # print('Results: Ordered by period:')
    # for result in by_period:
    #     print('Period: {}, Multiplier: {}, PnL: {}'.format(result[0], result[1], result[2]))
    # print('Results: Ordered by Profit:')
    # for result in by_PnL:
    #     print('Period: {}, Multiplier: {}, PnL: {}'.format(result[0], result[1], result[2]))
    #
    # my_heatmap(final_results_list)


    #### pyfolio mode
    # Create a cerebro entity
    cerebro = bt.Cerebro()  # normal mode
    # Add a strategy
    cerebro.addstrategy(TrendFollowStrategy)
    # Add the Data Feed to Cerebro
    cerebro.adddata(data)
    # Set our desired cash start
    cerebro.broker.setcash(startcash)
    # Add a FixedSize sizer according to the stake
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    # Set the commission
    TWSE_commission = 1.425/1000 + 3/2000
    cerebro.broker.setcommission(commission=TWSE_commission)
    # Add trade log
    cerebro.addanalyzer(trade_list, _name='trade_list')
    # Run
    strats = cerebro.run()  # normal mode

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue()) # normal mode

    strat = strats[0]
    pyfoliozer = strat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
    import pyfolio as pf

    pf.create_full_tear_sheet(
        returns,
        positions=positions,
        transactions=transactions,
        live_start_date='2015-01-01')
