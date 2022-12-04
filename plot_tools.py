from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from backtrader import plot
import base64
from io import BytesIO

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

## https://community.backtrader.com/topic/1190/save-cerebro-plot-to-file/10
## grab the plot as an html image
def getBacktestChart(runstrats):

    plotter = plot.plot.Plot(use='Agg')
    backtestchart = ""
    for si, strat in enumerate(runstrats):
        rfig = plotter.plot(strat, figid=si * 100, numfigs=1)
        for f in rfig:
            buf = BytesIO()
            f.savefig(buf, bbox_inches='tight', format='png')
            imageSrc = base64.b64encode(buf.getvalue()).decode('ascii')
            backtestchart += f"<img src='data:image/png;base64,{imageSrc}'/>"

    return backtestchart