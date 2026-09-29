"""Единая светлая тема Qt Widgets."""

STYLE = """
QWidget { color: #20362f; font-size: 13px; }
QMainWindow, QWidget#shell, QWidget#page { background: #f5f7f5; }
QFrame#sidebar { background: #173f35; border: none; }
QLabel#brand { color: #ffffff; font-size: 23px; font-weight: 700; }
QLabel#sidebarNote { color: #abc6ba; font-size: 12px; }
QPushButton#nav { text-align: left; background: transparent; border: none;
    color: #c7dad1; border-radius: 9px; padding: 13px 15px; font-weight: 600; }
QPushButton#nav:checked { background: #2b5448; color: #ffffff; }
QPushButton#nav:hover { background: #244c40; }
QLabel#eyebrow { color: #518271; font-size: 11px; font-weight: 700; }
QLabel#title { font-size: 29px; font-weight: 700; color: #173f35; }
QLabel#subtitle, QLabel#muted { color: #74827b; }
QLabel#section { font-size: 16px; font-weight: 650; }
QLabel#badge { color: #32614e; background: #e6efe8; padding: 5px 10px;
    border-radius: 10px; font-size: 11px; font-weight: 600; }
QLabel#emptyTitle { font-size: 18px; font-weight: 600; }
QLabel#emptyIcon { color: #66957c; font-size: 38px; }
QFrame#card { background: #ffffff; border: 1px solid #e0e7e1; border-radius: 12px; }
QFrame#card QLabel { background: transparent; border: none; }
QPlainTextEdit, QLineEdit { background: #f9fbf9; border: 1px solid #dce5dd;
    border-radius: 8px; padding: 9px; selection-background-color: #cce6d7; }
QPlainTextEdit:focus, QLineEdit:focus { border: 1px solid #589676; }
QPushButton { background: #ffffff; border: 1px solid #d9e3dc; border-radius: 8px;
    padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: #eef5ef; border-color: #adcab9; }
QPushButton:pressed { background: #deebe2; }
QPushButton:disabled { background: #f0f3f0; color: #9ba69e; border-color: #e5eae5; }
QPushButton#primary { background: #25664b; color: #ffffff; border-color: #25664b; }
QPushButton#primary:hover { background: #1c533d; }
QPushButton#primary:disabled { background: #b5c9bd; border-color: #b5c9bd; color: #f9fbf9; }
QPushButton#quiet { background: transparent; color: #62796a; border: none; padding: 6px; }
QPushButton#stop { color: #99583b; background: #fff4ed; border-color: #f0d6c5; }
QPushButton#stop:disabled { color: #bcaea5; background: #f6f2ef; border-color: #e9e3df; }
QTableWidget { background: #ffffff; alternate-background-color: #f8faf8; border: none;
    gridline-color: #edf1ed; selection-background-color: #e0eee5; selection-color: #173f35; }
QTableWidget::item { border-bottom: 1px solid #edf1ed; padding: 6px; }
QHeaderView::section { background: #f2f6f2; color: #7b887f; border: none;
    padding: 9px; font-size: 11px; font-weight: 600; }
QProgressBar { border: none; background: #e6ede7; border-radius: 4px;
    text-align: center; min-height: 7px; max-height: 7px; }
QProgressBar::chunk { background: #4a936b; border-radius: 4px; }
QLabel#notice { background: #eaf2ec; color: #365d46; padding: 9px 12px; border-radius: 8px; }
QLabel#notice[error="true"] { background: #fff0e7; color: #99542f; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: #173f35; color: #ffffff; border: none; padding: 6px; }
"""
