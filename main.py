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



if __name__ == '__main__':
    startcash = 1000000
    TWSE_commission = 1.425 / 1000 + 3 / 2000
    full_data = np.load('../datas/個股期標的歷史股價.npy', allow_pickle='TRUE').item()
    final_results_list = []

    # Prepare data
    dataframe = full_data['2892']
    dataframe.reset_index(inplace=True)
    dataframe.rename(columns={'Date': 'datetime'}, inplace=True)
    dataframe.drop(['Close'], axis=1)
    dataframe.rename(columns={'Adj Close':'close'}, inplace=True)
    dataframe.set_index('datetime', inplace=True)
    dataframe['openinterest'] = 0
    data = bt.feeds.PandasData(dataname=dataframe, fromdate=datetime.datetime(2010, 1, 1), todate=datetime.datetime(2022, 12, 31))

    #### normal mode
    # Create a cerebro entity
    cerebro = bt.Cerebro()  # normal mode
    # Add a strategy
    cerebro.addstrategy(stg.TrendFollowStrategy)
    # Add the Data Feed to Cerebro
    cerebro.adddata(data)
    # Set our desired cash start
    cerebro.broker.setcash(startcash)
    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.PercentSizer, percents=50)
    # Set the commission
    cerebro.broker.setcommission(commission=TWSE_commission)
    # Add trade log
    cerebro.addanalyzer(log_tools.trade_list, _name='trade_list')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='PyFolio')
    # Run
    strats = cerebro.run(tradehistory=True)  # normal mode
    # get analyzers data, comment out when optimizing
    trade_list = strats[0].analyzers.trade_list.get_analysis()  # normal mode
    print(tabulate(trade_list, headers="keys"))  # normal mode
    # quantstats
    portfolio_stats = strats[0].analyzers.getbyname('PyFolio')
    returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
    returns.index = returns.index.tz_convert(None)
    quantstats.reports.html(returns, output='stats.html')

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue()) # normal mode

    # Plot the result
    # cerebro.plot(iplot=False)  # using 'iplot=False' to avoid error message

    # # ####
    # # ####
    # # ####
    # # #### optimize mode
    # cerebro = bt.Cerebro(optreturn=False)  # optimize mode
    # # Add a strategy
    # # cerebro.optstrategy(TrendFollowStrategy, volumePeriod = range(30, 50), volumeMultiplier = range(10, 30))
    # cerebro.optstrategy(TrendFollowStrategy, volumePeriod = range(30, 31), volumeMultiplier = range(10, 15))
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
    # plot_tools.my_heatmap(final_results_list)


    # # ####
    # # ####
    # # ####
    # # #### Mass backtrade mode
    # for column in full_data:
    #     if column != 'TWII':
    #         dataframe = full_data[column]
    #         dataframe.reset_index(inplace=True)
    #         dataframe.rename(columns={'Date': 'datetime'}, inplace=True)
    #         dataframe.drop(['Close'], axis=1)
    #         dataframe.rename(columns={'Adj Close': 'close'}, inplace=True)
    #         dataframe.set_index('datetime', inplace=True)
    #         dataframe['openinterest'] = 0
    #         data = bt.feeds.PandasData(dataname=dataframe, fromdate=datetime.datetime(2015, 1, 1),
    #                                    todate=datetime.datetime(2022, 11, 30))
    #
    #         # Create a cerebro entity
    #         cerebro = bt.Cerebro()  # normal mode
    #         # Add a strategy
    #         cerebro.addstrategy(stg.TrendFollowStrategy)
    #         # Add the Data Feed to Cerebro
    #         cerebro.adddata(data)
    #         # Set our desired cash start
    #         cerebro.broker.setcash(startcash)
    #         # Add a FixedSize sizer according to the stake
    #         cerebro.addsizer(bt.sizers.PercentSizer, percents = 50)
    #         # Set the commission
    #         cerebro.broker.setcommission(commission=TWSE_commission)
    #         # Run
    #         strats = cerebro.run(tradehistory=True)  # normal mode
    #
    #         # prepare final result
    #         value = cerebro.broker.getvalue()
    #         PnL = round(value - startcash)
    #         final_results_list.append([column, PnL])
    #
    # total_PnL = 0
    # for result in final_results_list:
    #     print('Stock: {}, PnL: {}'.format(result[0], result[1]))
    #     total_PnL += result[1]
    #
    # print('Total PnL:{}'.format(total_PnL))