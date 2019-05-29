import time

import ipywidgets
from IPython.display import display


class ProgressBar():

    def __init__(self, n=0, hide=False):
        self._times = []
        self._progress = ipywidgets.IntProgress(min=0, max=n)
        self._text = ipywidgets.HTML()
        self.widget = ipywidgets.HBox([self._progress, self._text])
        self.reset(n)
        if not hide:
            display(self.widget)

    def close(self, clear=False):
        self._progress.max = self._progress.value
        if clear:
            self.widget.close()
        else:
            self._progress.bar_style = 'success'

    def reset(self, n=None):
        self._progress.value = 0
        if n is not None:
            self._progress.max = n
        self._progress.bar_style = 'info'
        self._times = [time.time()]

    def update(self, value=1):
        self._times.append(time.time())
        self._progress.value += value
        if self._progress.max and self._progress.value != self._progress.max:
            percentage = 100 * self._progress.value / self._progress.max if self._progress.max else 0
            time_ = (100 - percentage) * (self._times[-1] - self._times[0]) / percentage if percentage else 0
            text = 'remaining'
        else:
            time_ = self._times[-1] - self._times[0]
            text = 'elapsed'
        self._text.value = '<code>{}/{} ({:>.1f} {} {})</code>'.format(self._progress.value, self._progress.max, *self._interpret_time(time_), text)

    def _interpret_time(self, time):
        if time < 60:
            return time, 's'
        elif time < 60 * 60:
            return time / 60, 'min'
        elif time < 60 * 60 * 24:
            return time / (60 * 60), 'hr'
        elif time < 60 * 60 * 24 * 7:
            return time / (60 * 60 * 24), 'days'
        else:
            return time / (60 * 60 * 24 * 7), 'weeks'
