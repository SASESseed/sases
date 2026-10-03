"""SASES 启动器主窗口。"""
import os, sys
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QMainWindow, QWidget, QPushButton, QPlainTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox

# 项目根目录（launcher/ui/main_window.py -> 上溯三层）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.proc = None
        self.setWindowTitle('SASES 启动器')
        self.resize(900, 600)
        self.btn_start = QPushButton('启动')
        self.btn_stop = QPushButton('停止')
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        h = QHBoxLayout()
        h.addWidget(self.btn_start)
        h.addWidget(self.btn_stop)
        h.addStretch(1)
        v = QVBoxLayout()
        v.addLayout(h)
        v.addWidget(self.log)
        w = QWidget()
        w.setLayout(v)
        self.setCentralWidget(w)
        self.statusBar().showMessage('未运行')
        self.btn_stop.setEnabled(False)

    def out(self, t):
        self.log.appendPlainText(t.rstrip())

    def start(self):
        if self.proc:
            return
        p = QProcess(self)
        p.setWorkingDirectory(ROOT)
        p.readyReadStandardOutput.connect(self.read)
        p.readyReadStandardError.connect(self.read)
        p.finished.connect(self.done)
        p.start(sys.executable, ['scripts/run_forever.py'])
        self.proc = p
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.statusBar().showMessage('运行中')
        self.out('[启动器] 已启动 SASES 服务')

    def read(self):
        b = self.proc.readAllStandardOutput() + self.proc.readAllStandardError()
        for line in bytes(b).decode('utf-8', 'ignore').splitlines():
            self.out(line)

    def done(self, code, st):
        self.out('[启动器] 进程结束 code=%s' % code)
        self.proc = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.statusBar().showMessage('未运行')

    def stop(self):
        if not self.proc:
            return
        pid = int(self.proc.processId())
        QProcess.startDetached('taskkill', ['/F', '/T', '/PID', str(pid)])
        self.out('[启动器] 已停止 pid=%s' % pid)

    def closeEvent(self, e):
        if self.proc:
            r = QMessageBox.question(self, '确认', '服务还在运行，确定退出？')
            if r != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
            self.stop()
        e.accept()
