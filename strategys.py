import indicators as ind
import backtrader as bt

# 待辦：用跨度 / 時間比來調整持倉部位
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
        self.heavyTrade = ind.heavyTrade(self.datas[0].volume, period=self.params.volumePeriod, multiplier=self.params.volumeMultiplier/10)
        self.SuperTrend = ind.SuperTrend(self.datas[0], period=self.params.trendPeriod, multiplier=self.params.trendMultiplier)

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