from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from electrum.plugin import hook
from electrum.i18n import _
from electrum.gui.qt.util import TaskThread

from .labels import LabelsPlugin

if TYPE_CHECKING:
    from electrum.gui.qt.main_window import ElectrumWindow
    from electrum.wallet import Abstract_Wallet


class QLabelsSignalObject(QObject):
    labels_changed_signal = pyqtSignal(object)


class Plugin(LabelsPlugin):

    def __init__(self, *args):
        LabelsPlugin.__init__(self, *args)
        self.obj = QLabelsSignalObject()
        self._init_qt_received = False

    @hook
    def init_menubar(self, window: 'ElectrumWindow'):
        wallet = window.wallet
        if not wallet.get_fingerprint():
            return
        m = window.wallet_menu.addMenu('LabelSync')
        m.addAction("Force upload", lambda: self.do_push(window))
        m.addAction("Force download", lambda: self.do_pull(window))

    def do_push(self, window: 'ElectrumWindow'):
        thread = TaskThread(window)
        thread.add(
            partial(self.push, window.wallet),
            partial(self.done_processing_success, window),
            thread.stop,
            partial(self.done_processing_error, window))

    def do_pull(self, window: 'ElectrumWindow'):
        thread = TaskThread(window)
        thread.add(
            partial(self.pull, window.wallet, True),
            partial(self.done_processing_success, window),
            thread.stop,
            partial(self.done_processing_error, window))

    def on_pulled(self, wallet: 'Abstract_Wallet'):
        self.obj.labels_changed_signal.emit(wallet)

    def done_processing_success(self, dialog, result):
        dialog.show_message(_("Your labels have been synchronised."))

    def done_processing_error(self, dialog, exc_info):
        self.logger.error("Error synchronising labels", exc_info=exc_info)
        dialog.show_error(_("Error synchronising labels") + f':\n{repr(exc_info[1])}')

    @hook
    def load_wallet(self, wallet: 'Abstract_Wallet', window: 'ElectrumWindow'):
        self.obj.labels_changed_signal.connect(window.update_tabs)
        self.start_wallet(wallet)

    @hook
    def on_close_window(self, window):
        try:
            self.obj.labels_changed_signal.disconnect(window.update_tabs)
        except TypeError:
            pass  # 'method' object is not connected
        self.stop_wallet(window.wallet)
