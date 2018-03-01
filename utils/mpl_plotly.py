"""
A matplotlib-esque interface for Plotly-based interactive plots for the Jupyter
notebook.
"""



import matplotlib.pyplot as mplt
import plotly.offline as py
import plotly.graph_objs as go

py.offline.init_notebook_mode()

class PyplotPlot(object):
    def show(self):
        mplt.show()


class Figure(object):
    from . import utils
    """Class containing the equivalent of a matplotlib Axis."""
    def __init__(self):
        self.traces = []
        self.xaxis = {'exponentformat': 'power'}
        self.yaxis = {'exponentformat': 'power'}
        self.layout = {'xaxis': self.xaxis, 'yaxis': self.yaxis}


    def plot(self, *args, **kwargs):
        if 'color' in kwargs: color = kwargs['color']; del kwargs['color']
        else: color =  None
        if 'label' in kwargs: label = kwargs['label']; del kwargs['label']
        else: label =  None
        if 'mode' in kwargs: mode = kwargs['mode']; del kwargs['mode']
        else: mode = 'lines'
        """
        Add a curve to the figure.
        kwargs are passed through to the argument dictionary for go.Scatter.
        """
        if len(args) == 2:
            x, y = args
        elif len(args) == 1:
            x, y = list(range(len(args[0]))), args[0]
        else:
            raise ValueError("Plot accepts one or two positional arguments")
        scatter_kwargs = dict(x = x, y = y, name = label,
                line = dict(color = color), mode = mode)
        if label is None and mode == 'lines':
            scatter_kwargs['showlegend'] = False
            scatter_kwargs['hoverinfo'] = 'none'
            
        else:
            scatter_kwargs['showlegend'] = True
        self.traces.append(
            go.Scatter(**Figure.utils.merge_dicts(scatter_kwargs, kwargs)))

    def hist(self, x, alpha = .75, bins = None, color = None, label = None, **kwargs):
        # TODO: control number of bins
        default = dict(
            x = x,
            opacity = alpha,
            name = label,
            marker = dict(color = color)
        )
        self.traces.append(go.Histogram(**Figure.utils.merge_dicts(default, kwargs)))
        self.layout['barmode'] = 'overlay'

    def scatter(self, *args, **kwargs):
        kwargs['mode'] = 'markers'
        self.plot(*args, **kwargs)

    def set_xlabel(self, xlabel):
        self.xaxis['title'] = xlabel

    def set_ylabel(self, ylabel):
        self.yaxis['title'] = ylabel

    def set_xlim(self, range_tuple):
        self.xaxis['range'] = list(range_tuple)
        
    def set_ylim(self, range_tuple):
        self.yaxis['range'] = list(range_tuple)

    def set_xlim(self, range_tuple):
        self.xaxis['range'] = list(range_tuple)
        
    def set_ylim(self, range_tuple):
        self.yaxis['range'] = list(range_tuple)

    def set_title(self, title):
        self.layout['title'] = title

    def set_xscale(self, value):
        if value == 'log':
            self.xaxis['type'] = 'log'
        else:
            raise NotImplementedError

    def set_yscale(self, value):
        if value == 'log':
            self.yaxis['type'] = 'log'
        else:
            raise NotImplementedError

    def show(self,save=False):
        imagestr=None
        data = self.traces
        fig = go.Figure(data = data, layout = go.Layout(**self.layout))
        if save:
            imagestr = 'avg'
        py.iplot(fig, image = imagestr)

class Plt(object):
    def __init__(self):
        self.mode = None
        self.figures = []
        self.plt_global = None
    
    def _clear(self):
        self.__init__()

    def _get_global_plot(self):
        """
        Return the Figure instance for this object, creating it if necessary.
        """
        if self.plt_global is None:
            self.plt_global = Figure()
            self.figures.append(self.plt_global)
        return self.plt_global

    def subplots(self, *args, **kwargs):
        self.mode = 'plotly'
        if len(args) > 0:
            n_plots = args[0]
            self.figures = [Figure() for _ in range(n_plots)]
            return None, self.figures
        else:
            self.figures.append(Figure())
            return None, self.figures[0]

    def plot(self, *args, **kwargs):
        self._get_global_plot().plot(*args, **kwargs)

    def hist(self, *args, **kwargs):
        self._get_global_plot().hist(*args, **kwargs)

    def scatter(self, *args, **kwargs):
        self._get_global_plot().scatter(*args, **kwargs)

    def xlabel(self, xlabel):
        self._get_global_plot().set_xlabel(xlabel)

    def ylabel(self, ylabel):
        self._get_global_plot().set_ylabel(ylabel)

    def xscale(self, scale):
        self._get_global_plot().set_xscale(scale)

    def ylim(self, range_tuple):
        self._get_global_plot().set_ylim(range_tuple)

    def xlim(self, range_tuple):
        self._get_global_plot().set_xlim(range_tuple)

    def yscale(self, scale):
        self._get_global_plot().set_yscale(scale)

    def title(self, title):
        self._get_global_plot().set_title(title)

    def legend(self):
        pass

    def show(self,save=False):
        for fig in self.figures:
            fig.show(save=save)
        self._clear()

    def imshow(self, *args, **kwargs):
        mplt.imshow(*args, **kwargs)
        self.figures.append(PyplotPlot())

    def savefig(self, *args, **kwargs):
        # TODO: implement this
        pass


plt = Plt()
