import backtrader as bt
import statistics

class heavyTrade(bt.Indicator):
    lines = ('heavyTrade',)
    params = (('period', 30),('multiplier',1.5))
    # plotinfo = dict(subplot=False)

    def __init__(self):
        self.lines.heavyTrade = self.data > self.p.multiplier * bt.ind.MaxN(self.data(-1), period=self.p.period)


class HevayTradeByPercentile(bt.Indicator):
    lines = ("HeavyTrade", )

    params = (
        ("period", 30),
        ("multiplier", 2),
        ("percentile", 90),
    )

    def __init__(self):
        self.addminperiod(self.p.period)

    def next(self):
        volume_array = self.data.get(size=self.p.period)   # 取得過去一段時間內的成交量
        a = [round(q, 1) for q in statistics.quantiles(volume_array, n=10)]  # 計算百分位（以 10% 為單位）
        x = -(100-self.p.percentile)/10  # 計算取得第幾十趴的成交量
        self.l.HeavyTrade[0] = self.data[0] > self.p.multiplier * a[int(x)]
        # logging
        # print(self.data[0], self.p.multiplier * a[int(x)])

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