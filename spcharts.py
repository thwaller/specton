import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
plt.style.use(['ggplot'])
from PyQt5.QtWidgets import QSizePolicy

class Bitrate_Chart(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100, x=[], y=[]):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # We want the axes cleared every time plot() is called
        self.axes.hold(False)

        self.compute_initial_figure(x,y)

        #
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self,x,y):
         self.axes.bar(x,y,width=20,align='center')
         self.axes.set_ylabel('Number of frames')
         self.axes.set_xlabel('Bitrate (Kbps)')
         self.axes.set_xticks([32,64,96,128,160,192,224,256,288,320,352,384])

class BitGraph(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100, x=[], y=[]):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # We want the axes cleared every time plot() is called
        self.axes.hold(False)

        self.compute_initial_figure(x,y)

        #
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self,x,y):
        max = 0
        min = 999999999
        for num in y:
            if num > max:
                max = num
            if num < min:
                min = num
        self.axes.plot(x,y)
        self.axes.set_ylabel('Bitrate (Kb/s)')
        self.axes.set_xlabel('Time (s)')
        x_lim = x[len(x)-1]
        self.axes.set_ylim(min*0.9,max*1.1)
        self.axes.set_xlim(0,x_lim)