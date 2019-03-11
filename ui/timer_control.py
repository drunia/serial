#!/usb/bin/env python3
# -*- coding: utf-8 -*-


from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPaintEvent, QPainter, QPixmap, QPalette, QColor, QPen
from PyQt5.QtWidgets import *
from configparser import ConfigParser
import datetime, enum, pt


class ControlMode(enum.Enum):
    """Enumeration for control modes"""
    # Control modes:
    # FREE - work infinity
    # CASH - calculate time by taked cash
    # TIME - calculating time
    TIME = 0
    CASH = 1
    FREE = 2


class EditTimeMode(enum.Enum):
    """Enumeration for edit mode in time display"""
    NO_EDIT = 0
    HOURS = 1
    MINUTES = 2


class TimerCashControl(QFrame):
    """ Control for channel"""

    """ 
    Switch signal
    :param object - instance of TimerCashControl
    :param bool - switch state
    """
    switched = pyqtSignal(object, bool)

    def __init__(self, parent: QWidget, num_channel: int):
        """
        Create control UI by channel
        :param parent: Parent component
        :param num_channel: Number of switchable channel (from active plugin)
        """
        super().__init__(parent)

        # current control mode
        self.mode = ControlMode.FREE
        self.time = 0
        self.cash = 0
        self.price = 80
        self.channel = num_channel
        # can displayed time (for blinking time in pause)
        self.displayed = True
        # timer paused
        self.paused = False
        # timer stopped
        self.stopped = True
        self.timer_id = 0
        self.edit_time_mode = EditTimeMode.NO_EDIT
        # Edit peace of time
        self.tmp_edit_time = {
            "time_str": "",
            "time_editable_peace": ""
        }

        # last second for indicating (blinking) control mode
        self.time_repaint_mode = datetime.datetime.now().second

        # Tariffs
        self.config: ConfigParser = self.parent().config
        if self.config.has_section(pt.TARIFFS_CONF_SECTION):
            self.tariffs = self.config[pt.TARIFFS_CONF_SECTION]
        else:
            self.tariffs = {}

        print(self.tariffs)

        # Timer
        self.timer = QTimer()
        self.timer.timerEvent = self._timerEvent
        self.timer_id = self.timer.startTimer(100, Qt.PreciseTimer)

        # Icons
        self.cash_pixmap = QPixmap("./res/cash.png")
        self.time_pixmap = QPixmap("./res/clock.png")

        # UI
        self._init_ui()
        self.display()

        # Test timeout signal
        self.switched.connect(lambda *x: print("Switch signal:", x))

    def _init_ui(self):
        # Set minimum size
        self.setMinimumSize(310, 260)
        self.setMaximumSize(380, 340)
        self.setFrameStyle(QFrame.Box)

        # Title (Number of channel)
        self.tittle_lb = QLabel()
        self.tittle_lb.setText("Канал " + str(self.channel+1))
        f: QFont = self.tittle_lb.font()
        f.setPointSize(20)
        self.tittle_lb.setFont(f)
        self.tittle_lb.setAlignment(Qt.AlignLeft)

        # Time
        self.time_display = QLCDNumber()
        self.time_display.setDigitCount(10)
        self.time_display.setSegmentStyle(QLCDNumber.Flat)
        self.time_display.paintEvent = self._time_paint_event
        self.time_display.setAutoFillBackground(True)
        self.time_display.setFocusPolicy(Qt.ClickFocus)
        self.time_display.setCursor(Qt.IBeamCursor)

        # set background color
        p: QPalette = self.time_display.palette()
        p.setColor(QPalette.Background, QColor(204, 204, 204))
        self.time_display.setPalette(p)

        self.time_display.focusInEvent = self._time_focus_in
        self.time_display.focusOutEvent = self._time_focus_out
        self.time_display.keyPressEvent = self._time_key_pressed

        # $Cash
        self.cash_display = QLCDNumber()
        self.cash_display.setDigitCount(8)
        self.cash_display.display(self.cash)
        self.cash_display.setSegmentStyle(QLCDNumber.Flat)
        self.cash_display.paintEvent = self._cash_paint_event
        self.cash_display.setAutoFillBackground(True)
        self.cash_display.setFocusPolicy(Qt.ClickFocus)
        self.cash_display.setCursor(Qt.IBeamCursor)

        # set background color
        self.cash_display.setPalette(p)

        self.cash_display.focusInEvent = self._cash_focus_in
        self.cash_display.focusOutEvent = self._cash_focus_out
        self.cash_display.keyPressEvent = self._cash_key_pressed

        # Get default display background color
        p: QPalette = self.cash_display.palette()
        self.default_background_display_color = p.color(QPalette.Background)

        # Controls
        self.start_btn = QPushButton("Старт")
        self.start_btn.setMinimumSize(100, 20)
        self.start_btn.clicked.connect(self.start)
        self.start_btn.setAutoDefault(True)

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setMinimumSize(100, 20)
        self.stop_btn.clicked.connect(self.stop)

        # Root layout
        root_lay = QVBoxLayout(self)
        root_lay.addWidget(self.tittle_lb, stretch=0)
        root_lay.addWidget(self.time_display, stretch=1)
        root_lay.addWidget(self.cash_display, stretch=1)

        # Controls layout
        controls_lay = QHBoxLayout(self)
        controls_lay.addWidget(self.start_btn)
        controls_lay.addWidget(self.stop_btn)
        controls_lay.setContentsMargins(0, 10, 0, 5)

        root_lay.addLayout(controls_lay)

    # Timer
    def _timerEvent(self, evt):
        if self.stopped:
            self.displayed = True
            return
        if self.paused:
            self.displayed = not self.displayed
        else:
            self.displayed = True
            if self.mode == ControlMode.FREE:
                self.time += 1
            elif self.time == 0:
                # Time  is UP!
                self.time_out()
            else:
                self.time -= 1
        self.display()

    def time_out(self):
        self.stop()
        QMessageBox.information(self, self.tittle_lb.text(), "Время вышло!", QMessageBox.Ok)

    # Display time & cash
    def display(self):
        self.cash = self.time * (self.price / 3600)
        # Time
        if self.displayed:
            str_time = "{:0>8}".format(str(datetime.timedelta(seconds=self.time)))
        else:
            str_time = ""
        # Cash
        str_cash = "{:.2f}".format(self.cash)
        # Display values
        self.time_display.display(str_time)
        self.time_display.update()
        self.cash_display.display(str_cash)
        self.cash_display.update()

    # Start / Pause timer
    def start(self):
        self.time_display.setFocusPolicy(Qt.NoFocus)
        self.cash_display.setFocusPolicy(Qt.NoFocus)

        if self.cash == 0 and self.time == 0:
            self.mode = ControlMode.FREE

        if self.stopped:
            self.stopped = False
            self.start_btn.setText("Пауза")
            self.switched.emit(self, True)
            return

        if self.paused:
            self.start_btn.setText("Пауза")
            self.paused = False
            self.switched.emit(self, True)
        else:
            self.start_btn.setText("Возобновить")
            self.paused = True
            self.switched.emit(self, False)
        self.display()

    # Stop timer
    def stop(self):
        if self.stopped: return
        if (self.cash or self.time) and \
            QMessageBox.No == QMessageBox.question(
                self, self.tittle_lb.text(), "Завершить текущий сеанс?",
                QMessageBox.Yes | QMessageBox.No
            ): return

        self.time_display.setFocusPolicy(Qt.ClickFocus)
        self.cash_display.setFocusPolicy(Qt.ClickFocus)

        self.start_btn.setText("Старт")

        # Set default mode to FREE
        self.mode = ControlMode.FREE

        self.displayed = True
        self.paused = False
        self.stopped = True
        self.cash = 0
        self.time = 0
        self.display()

        self.switched.emit(self, False)

    # Paint cash icon in QLCDNumber
    def _cash_paint_event(self, evt: QPaintEvent):
        p: QPainter = QPainter(self.cash_display)
        w, h = 0, self.cash_display.height() - (p.fontMetrics().height() / 2)
        p.drawText((p.fontMetrics().height() / 2), h, "Деньги")

        # Blinking icon to indicate control mode when cash < by 5 min for price
        if not self.stopped and not self.paused and \
                self.cash < (self.price / 3600 * (5 * 60)) and \
                self.mode != ControlMode.FREE and \
                datetime.datetime.now().second % 2:
            QLCDNumber.paintEvent(self.cash_display, evt)
            return

        if self.mode != ControlMode.TIME:
            w, h = 32, 32
            p.drawPixmap(5, 5, w, h, self.cash_pixmap)

        QLCDNumber.paintEvent(self.cash_display, evt)

    # Paint clock icon in QLCDNumber
    def _time_paint_event(self, evt: QPaintEvent):
        p: QPainter = QPainter(self.time_display)
        w, h = 0, self.time_display.height() - (p.fontMetrics().height() / 2)
        p.drawText((p.fontMetrics().height() / 2), h, "Время")

        # Blinking icon to indicate control mode when 5 minutes left
        if not self.stopped and not self.paused and \
                self.time < (5 * 60) and \
                self.mode != ControlMode.FREE and \
                datetime.datetime.now().second % 2:
            QLCDNumber.paintEvent(self.time_display, evt)
            return

        if self.mode != ControlMode.CASH:
            w, h = 32, 32
            p.drawPixmap(5, 5, w, h, self.time_pixmap)

        # Edit time
        if self.edit_time_mode != EditTimeMode.NO_EDIT:
            pos_num = 0
            if self.edit_time_mode == EditTimeMode.HOURS:
                pos_num = 2
            if self.edit_time_mode == EditTimeMode.MINUTES:
                pos_num = 5
            pen: QPen = p.pen()
            pen.setWidth(2)
            pen.setCapStyle(Qt.FlatCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            dig_width = self.time_display.width() / self.time_display.digitCount()
            dig_height = self.time_display.height() / 2
            margin = dig_width / 4
            x1 = (dig_width * pos_num) - margin
            y1 = (dig_height / 2) - margin
            x2 = (dig_width * 2) + margin * 2
            y2 = dig_height + margin * 2
            p.drawRoundedRect(x1, y1, x2, y2, 5.0, 5.0)

        QLCDNumber.paintEvent(self.time_display, evt)

    # Cash display get focus
    def _cash_focus_in(self, evt):
        print("cash_focus_in")
        palette: QPalette = self.cash_display.palette()
        palette.setColor(QPalette.Background, QColor(255, 255, 255))
        self.cash_display.setPalette(palette)

        print(self.cash)
        try:
            if float(self.cash).is_integer():
                self.cash = str(int(float(self.cash)))
            else:
                self.cash = str(round(self.cash, 2))
        except Exception as e:
            print(e)
        # Set control mode by cash
        self.mode = ControlMode.CASH
        self.cash_display.display(self.cash)
        self.time_display.update()

    # Cash display lost focus
    def _cash_focus_out(self, evt):
        print("cash_focus_out")
        pallete: QPalette = self.cash_display.palette()
        pallete.setColor(QPalette.Background, self.default_background_display_color)
        self.cash_display.setPalette(pallete)
        self.cash = round(float(self.cash), 2)
        # Check max cash by 24 hours
        max_cash = ((24 * 3600) - 1) * (self.price / 3600)
        if self.cash > max_cash:
            self.cash = max_cash
        # Calculate time by cash
        self.time = round(self.cash / (self.price / 3600))
        self.display()
        self.start_btn.setFocus()

    # Cash display key pressed
    def _cash_key_pressed(self, evt):
        # In edit mode , we work ONLY with str type self.cash
        if evt.key() == Qt.Key_Enter or evt.key() == Qt.Key_Return:
            self.cash_display.clearFocus()
        if (Qt.Key_0 <= evt.key() <= Qt.Key_9) or \
                (evt.key() == Qt.Key_Period or evt.key() == Qt.Key_Backspace):
            cash = str(self.cash)
            if evt.key() == Qt.Key_Backspace and len(cash) > 0:
                cash = cash[:-1]
            elif len(cash) == 1 and cash[0] == "0" and \
                    evt.key() != Qt.Key_Period and Qt.Key_1 <= evt.key() <= Qt.Key_9:
                cash = evt.text()
            elif evt.key() == Qt.Key_0 and len(cash) == 1 and cash[0] == "0":
                pass
            elif evt.key() == Qt.Key_Period and "." in cash:
                pass
            elif "." in cash and len(cash) - cash.index(".") == 3:
                pass
            elif len(cash) > self.cash_display.digitCount() - 2 or \
                    "." not in cash and len(cash) >= self.cash_display.digitCount() - 4 and \
                    evt.key() != Qt.Key_Period:
                pass
            else:
                cash += evt.text()
            self.cash = cash if len(cash) > 0 else "0"
            self.cash_display.display(self.cash)

    # Time display get focus
    def _time_focus_in(self, evt):
        print("time_focus_in")
        pallete: QPalette = self.time_display.palette()
        pallete.setColor(QPalette.Background, QColor(255, 255, 255))
        self.time_display.setPalette(pallete)
        self.edit_time_mode = EditTimeMode.HOURS
        # Set control mode by time
        self.mode = ControlMode.TIME
        self.cash_display.update()
        # For edit peace
        self.tmp_edit_time["time_str"] = "{:0>8}".format(str(datetime.timedelta(seconds=self.time)))


    # Time display lost focus
    def _time_focus_out(self, evt):
        print("time_focus_out")
        palette: QPalette = self.time_display.palette()
        palette.setColor(QPalette.Background, self.default_background_display_color)
        self.time_display.setPalette(palette)
        self.edit_time_mode = EditTimeMode.NO_EDIT
        self.display()
        self.start_btn.setFocus()

    # Time display key pressed
    def _time_key_pressed(self, evt):
        if evt.key() == Qt.Key_Enter or evt.key() == Qt.Key_Return:
            self.time_display.clearFocus()
        legal_keys = (Qt.Key_Left, Qt.Key_Right, Qt.Key_Plus, Qt.Key_Minus, Qt.Key_Enter, Qt.Key_Return)
        if not (Qt.Key_0 <= evt.key() <= Qt.Key_9) and evt.key() not in legal_keys: return

        if evt.key() == Qt.Key_Left or evt.key() == Qt.Key_Right:
            if self.edit_time_mode == EditTimeMode.HOURS:
                self.edit_time_mode = EditTimeMode.MINUTES
                self.time_display.update()
                return
            elif self.edit_time_mode == EditTimeMode.MINUTES:
                self.edit_time_mode = EditTimeMode.HOURS
                self.time_display.update()
                return
        if evt.key() == Qt.Key_Plus:
            if self.edit_time_mode == EditTimeMode.HOURS:
                if self.time <= (23 * 3600) - 1:
                    self.time += 3600
                else:
                    self.edit_time_mode = EditTimeMode.MINUTES
                    self.time_display.update()
            if self.edit_time_mode == EditTimeMode.MINUTES:
                if self.time <= (24 * 3600) - 61:
                    self.time += 60
            if (24 * 3600) - self.time == 60:
                self.time += 59
            self.display()
            return
        if evt.key() == Qt.Key_Minus:
            if self.edit_time_mode == EditTimeMode.HOURS:
                if self.time >= 3600:
                    self.time -= 3600
                else:
                    self.edit_time_mode = EditTimeMode.MINUTES
                    self.time_display.update()
            if self.edit_time_mode == EditTimeMode.MINUTES:
                if self.time >= 60:
                    self.time -= 60
            if self.time < 60:
                self.time = 0
            self.display()

        if Qt.Key_0 <= evt.key() <= Qt.Key_9:
            self.tmp_edit_time["time_editable_peace"] = evt.text()



if __name__ == "__main__":
    import os, pt

    os.chdir("..")
    app = QApplication([])
    mw = QWidget()
    mw.config = pt.read_config()
    w = TimerCashControl(mw, 1)
    mw.show()
    app.exec()
