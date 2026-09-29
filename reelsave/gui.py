"""Графический интерфейс. Сетевой код вынесен в DownloadService и DownloadWorker."""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QFileDialog, QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from . import __version__
from .downloader import DownloadService
from .models import DownloadOptions, DownloadResult, Progress, QueueItem, Status
from .storage import Storage
from .worker import DownloadWorker
from .urls import parse_urls

RETRYABLE = {Status.WAITING, Status.ERROR, Status.CANCELLED}
COLORS = {
    Status.DONE: "#28764e", Status.SKIPPED: "#28764e", Status.ERROR: "#b3653a",
    Status.DOWNLOADING: "#28764e", Status.FETCHING: "#916d2c", Status.CANCELLED: "#8a8074",
}


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text: str, callback, name: str = "") -> QPushButton:
    widget = QPushButton(text)
    widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    return widget


def table(headers: list[str]) -> QTableWidget:
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.verticalHeader().hide()
    widget.verticalHeader().setDefaultSectionSize(49)
    widget.setShowGrid(False)
    widget.setAlternatingRowColors(True)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    widget.horizontalHeader().setStretchLastSection(True)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage, service: DownloadService | None = None):
        super().__init__()
        self.storage = storage
        self.service = service or DownloadService(storage)
        self.items: list[QueueItem] = []
        self.worker: DownloadWorker | None = None
        self.close_pending = False
        self.batch_total = 0
        self.batch_done = 0
        self.batch_counts: dict[Status, int] = {}
        self.setWindowTitle("ReelSave — Instagram Reels")
        self.resize(1150, 850)
        self.setMinimumSize(970, 780)
        shell = QWidget()
        shell.setObjectName("shell")
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._sidebar())
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)
        self.pages.addWidget(self._downloads_page())
        self.pages.addWidget(self._history_page())
        self.pages.addWidget(self._about_page())
        self.setCentralWidget(shell)
        self.nav_buttons[0].setChecked(True)
        self._update_controls()

    def _sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 31, 20, 24)
        layout.addWidget(label("▸ ReelSave", "brand"))
        layout.addWidget(label("Миті залишаються.", "sidebarNote"))
        layout.addSpacing(42)
        self.nav_buttons = []
        for index, title in enumerate(("↓   Завантаження", "◷   Історія", "ⓘ   Про проєкт")):
            nav = button(title, lambda checked=False, i=index: self._navigate(i), "nav")
            nav.setCheckable(True)
            layout.addWidget(nav)
            self.nav_buttons.append(nav)
        layout.addStretch()
        layout.addWidget(label("PYTHON + QT", "sidebarNote"))
        layout.addWidget(label(f"Навчальний проєкт · v{__version__}", "sidebarNote"))
        return sidebar

    def _page(self, title: str, subtitle: str):
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 26, 30, 24)
        layout.setSpacing(13)
        layout.addWidget(label("INSTAGRAM REELS  /  REELSAVE", "eyebrow"))
        layout.addWidget(label(title, "title"))
        layout.addWidget(label(subtitle, "subtitle", True))
        layout.addSpacing(5)
        return page, layout

    def _downloads_page(self):
        page, layout = self._page("Збережи мить.", "Встав посилання на Reel — відео збережеться на твоєму пристрої.")
        self.input_card = QFrame()
        self.input_card.setObjectName("card")
        card = QVBoxLayout(self.input_card)
        card.setContentsMargins(19, 16, 19, 15)
        card.setSpacing(10)
        header = QHBoxLayout()
        header.addWidget(label("01   Додай посилання", "section"))
        header.addStretch()
        header.addWidget(label("По одному в рядку", "muted"))
        card.addLayout(header)
        self.url_input = QPlainTextEdit()
        self.url_input.setObjectName("urlInput")
        self.url_input.setPlaceholderText("https://www.instagram.com/reel/…\nМожна вставити кілька посилань")
        self.url_input.setFixedHeight(78)
        self.url_input.setAccessibleName("Посилання на Reels")
        card.addWidget(self.url_input)
        actions = QHBoxLayout()
        actions.addWidget(button("Вставити", self._paste))
        actions.addWidget(button("Імпорт .txt", self._import_file))
        actions.addStretch()
        self.add_button = button("+  До черги", self._add_urls, "primary")
        actions.addWidget(self.add_button)
        card.addLayout(actions)
        card.addSpacing(2)
        card.addWidget(label("Зберегти в", "muted"))
        destination = QHBoxLayout()
        saved = self.storage.load_settings().get("output_dir")
        self.output_input = QLineEdit(saved if isinstance(saved, str) and saved else str(Path.home() / "Downloads/ReelSave"))
        self.output_input.setAccessibleName("Папка для відео")
        destination.addWidget(self.output_input, 1)
        destination.addWidget(button("Вибрати…", self._choose_output))
        card.addLayout(destination)
        access = QHBoxLayout()
        self.cookie_label = label("Без входу · публічні Reels", "muted")
        access.addWidget(self.cookie_label, 1)
        self.cookies_file: Path | None = None
        self.cookies_button = button("Підключити cookies…", self._choose_cookies, "quiet")
        self.cookies_button.setToolTip("Якщо Instagram вимагає входу: вибери cookies.txt у форматі Netscape.")
        access.addWidget(self.cookies_button)
        self.clear_cookies = button("×", self._clear_cookies, "quiet")
        self.clear_cookies.setToolTip("Відключити cookies")
        self.clear_cookies.hide()
        access.addWidget(self.clear_cookies)
        card.addLayout(access)
        layout.addWidget(self.input_card)

        self.notice = label("", "notice", True)
        self.notice.hide()
        layout.addWidget(self.notice)
        queue_header = QHBoxLayout()
        queue_header.addWidget(label("02   Черга завантажень", "section"))
        self.queue_count = label("0 відео", "badge")
        queue_header.addWidget(self.queue_count)
        queue_header.addStretch()
        self.remove_button = button("Видалити", self._remove_selected, "quiet")
        self.remove_button.setToolTip("Видалити вибрані рядки з черги; файли залишаться на диску.")
        self.clear_button = button("Очистити готові", self._clear_completed, "quiet")
        queue_header.addWidget(self.remove_button)
        queue_header.addWidget(self.clear_button)
        layout.addLayout(queue_header)

        self.queue_stack = QStackedWidget()
        empty = QFrame()
        empty.setObjectName("card")
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        for text, name in [("↓", "emptyIcon"), ("Твої Reels будуть тут", "emptyTitle"),
                           ("Додай посилання, вибери папку й натисни «Завантажити».", "muted")]:
            item = label(text, name)
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(item)
        empty_layout.addStretch()
        self.queue_stack.addWidget(empty)
        self.queue_table = table(["REEL", "СТАТУС", "ПРОГРЕС"])
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue_table.horizontalHeader().setStretchLastSection(False)
        self.queue_table.setColumnWidth(2, 110)
        self.queue_table.itemSelectionChanged.connect(self._selection_changed)
        self.queue_table.cellDoubleClicked.connect(self._open_queue_file)
        self.queue_stack.addWidget(self.queue_table)
        layout.addWidget(self.queue_stack, 1)
        self.queue_stack.setMinimumHeight(145)
        self.detail = label("Подвійне клацання на готовому відео відкриє файл.", "muted", True)
        layout.addWidget(self.detail)
        self.total_progress = QProgressBar()
        self.total_progress.setTextVisible(False)
        self.total_progress.setValue(0)
        layout.addWidget(self.total_progress)
        footer = QHBoxLayout()
        summary = QVBoxLayout()
        self.summary = label("Готовий до завантаження", "section")
        summary.addWidget(self.summary)
        summary.addWidget(label("Найкращий готовий потік із відео та звуком", "muted"))
        footer.addLayout(summary, 1)
        self.stop_button = button("Зупинити", self._stop, "stop")
        self.start_button = button("Завантажити", self._start, "primary")
        self.start_button.setMinimumWidth(144)
        self.start_button.setToolTip("Завантажити нові посилання та повторити зупинені або невдалі завантаження.")
        footer.addWidget(self.stop_button)
        footer.addWidget(self.start_button)
        layout.addLayout(footer)
        return page

    def _history_page(self):
        page, layout = self._page("Історія завантажень", "Останні 300 операцій зберігаються між запусками застосунку.")
        tools = QHBoxLayout()
        tools.addWidget(button("Оновити", self._refresh_history))
        tools.addStretch()
        tools.addWidget(button("Відкрити файл", self._open_history_file))
        tools.addWidget(button("Відкрити папку", self._open_history_folder))
        layout.addLayout(tools)
        self.history_table = table(["ДАТА", "ВІДЕО", "СТАТУС"])
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.cellDoubleClicked.connect(lambda *_: self._open_history_file())
        self.history_table.itemSelectionChanged.connect(self._history_selection)
        layout.addWidget(self.history_table, 1)
        self.history_detail = label("Історія поки порожня. Завантаж свій перший Reel.", "muted", True)
        self.history_detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.history_detail)
        self.history_rows: list[dict] = []
        return page

    def _about_page(self):
        page, layout = self._page("Простий інструмент.\nЗрозуміла будова.", "ReelSave · проєкт із кросплатформного програмування")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 8, 10, 0)
        for title, text in [
            ("Як користуватися", "1. Скопіюй посилання через «Поділитися → Копіювати посилання» в Instagram.\n"
             "2. Встав його в поле та додай до черги. Можна імпортувати файл .txt.\n"
             "3. Вибери папку й натисни «Завантажити». Готовий файл відкривається подвійним клацанням."),
            ("Якщо Instagram просить увійти", "Підключи файл cookies.txt у форматі Netscape зі свого браузера. "
             "Він надає доступ до сеансу облікового запису: не надсилай його іншим і не додавай до Git. "
             "Застосунок не запитує пароль і не запам’ятовує шлях до cookies після закриття."),
            ("Windows · macOS · Linux", "Один вихідний код на Python. PySide6 відповідає за вікно, "
             "yt-dlp — за отримання відео, SQLite — за історію. Завантаження відбувається в окремому потоці. "
             "Шляхи обробляються через pathlib; для відкриття файлів використовуються засоби Qt."),
            ("Якість та обмеження", "Зберігається найкращий доступний єдиний потік із відео та звуком, "
             "без перекодування. Окремі відео- й аудіодоріжки не об’єднуються; FFmpeg не потрібен. "
             "Instagram може обмежувати запити, вимагати входу або змінювати способи доступу. "
             "Використовуй застосунок для своїх роликів або контенту, який дозволено завантажувати."),
            ("Зупинка та повтор", "Кнопка «Зупинити» зупиняє чергу під час наступної відповіді завантажувача. "
             "Очікування відповіді мережі може тривати кілька секунд. Частковий .part-файл зберігається "
             "для продовження. Успішно завантажені файли повторно не завантажуються, поки вони є у вибраній папці."),
        ]:
            body.addWidget(label(title, "section"))
            body.addWidget(label(text, "muted", True))
            body.addSpacing(16)
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return page

    def _navigate(self, index: int):
        self.pages.setCurrentIndex(index)
        for i, nav in enumerate(self.nav_buttons):
            nav.setChecked(i == index)
        if index == 1:
            self._refresh_history()

    def _show_notice(self, text: str, error: bool = False):
        self.notice.setText(text)
        self.notice.setProperty("error", error)
        self.notice.style().unpolish(self.notice)
        self.notice.style().polish(self.notice)
        self.notice.show()

    def _paste(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_input.appendPlainText(text)
        else:
            self._show_notice("У буфері обміну немає тексту. Скопіюй посилання на Reel.", True)

    def _import_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Імпорт посилань", "", "Текстові файли (*.txt);;Усі файли (*)")
        if not filename:
            return
        try:
            self.url_input.appendPlainText(Path(filename).read_text(encoding="utf-8-sig"))
            self._add_urls()
        except (OSError, UnicodeError) as exc:
            self._show_notice(f"Не вдалося прочитати файл UTF-8: {exc}", True)

    def _add_urls(self):
        urls, errors = parse_urls(self.url_input.toPlainText())
        if errors:
            self._show_notice("Нічого не додано. Виправ посилання. " + " ".join(errors[:2]), True)
            return
        if not urls:
            self._show_notice("Спочатку встав хоча б одне посилання на Reel.", True)
            self.url_input.setFocus()
            return
        known = {item.url for item in self.items}
        added = [QueueItem(url) for url in urls if url not in known]
        self.items.extend(added)
        self.url_input.clear()
        self._render_queue()
        self._show_notice(f"Додано: {len(added)}. Повтори в черзі: {len(urls) - len(added)}.")

    def _render_queue(self):
        self.queue_table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            name = item.url.rstrip("/").rsplit("/", 1)[-1]
            cell = QTableWidgetItem(name)
            cell.setToolTip(item.url)
            self.queue_table.setItem(row, 0, cell)
            self._set_row_status(row, item.status)
            self.queue_table.setItem(row, 2, QTableWidgetItem("100%" if item.status in {Status.DONE, Status.SKIPPED} else "—"))
        self.queue_stack.setCurrentIndex(1 if self.items else 0)
        self.queue_count.setText(f"{len(self.items)} відео")
        self._update_controls()

    def _set_row_status(self, row: int, status: Status):
        cell = QTableWidgetItem(str(status))
        cell.setForeground(QColor(COLORS.get(status, "#7b887f")))
        cell.setToolTip(self.items[row].message)
        self.queue_table.setItem(row, 1, cell)

    def _update_controls(self):
        busy = self.worker is not None
        count = sum(item.status in RETRYABLE for item in self.items)
        self.input_card.setEnabled(not busy)
        self.remove_button.setEnabled(not busy and bool(self.queue_table.selectionModel().selectedRows()))
        self.clear_button.setEnabled(not busy and any(item.status in {Status.DONE, Status.SKIPPED} for item in self.items))
        self.start_button.setEnabled(not busy and count > 0)
        self.start_button.setText(f"Завантажити · {count}" if count else "Завантажити")
        self.stop_button.setEnabled(busy and not self.worker.stop_event.is_set())

    def _selection_changed(self):
        rows = self.queue_table.selectionModel().selectedRows()
        if rows and rows[0].row() < len(self.items):
            item = self.items[rows[0].row()]
            self.detail.setText(item.message or str(item.path or item.url))
        self._update_controls()

    def _remove_selected(self):
        for row in sorted((i.row() for i in self.queue_table.selectionModel().selectedRows()), reverse=True):
            del self.items[row]
        self._render_queue()
        self.detail.setText("Файли на диску зберігаються після видалення рядків із черги.")

    def _clear_completed(self):
        self.items = [item for item in self.items if item.status not in {Status.DONE, Status.SKIPPED}]
        self._render_queue()

    def _choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка для відео", self.output_input.text())
        if folder:
            self.output_input.setText(folder)

    def _choose_cookies(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Cookies у форматі Netscape", "", "Текстові файли (*.txt);;Усі файли (*)")
        if filename:
            self.cookies_file = Path(filename)
            self.cookie_label.setText("Cookies підключено")
            self.cookie_label.setToolTip(filename)
            self.cookies_button.setText("Змінити cookies…")
            self.clear_cookies.show()

    def _clear_cookies(self):
        self.cookies_file = None
        self.cookie_label.setText("Без входу · публічні Reels")
        self.cookie_label.setToolTip("")
        self.cookies_button.setText("Підключити cookies…")
        self.clear_cookies.hide()

    def _start(self):
        if self.worker is not None:
            return
        if not self.output_input.text().strip():
            self._show_notice("Вибери папку для збереження відео.", True)
            return
        jobs = [(row, item.url) for row, item in enumerate(self.items) if item.status in RETRYABLE]
        if not jobs:
            return
        if self.cookies_file and not self.cookies_file.is_file():
            self._show_notice("Файл cookies не знайдено. Підключи його знову або відключи cookies.", True)
            return
        options = DownloadOptions(Path(self.output_input.text().strip()).expanduser(), self.cookies_file)
        self.notice.hide()
        try:
            self.storage.save_settings(str(options.output_dir))
        except OSError as exc:
            self._show_notice(f"Не вдалося зберегти налаштування: {exc}", True)
        for row, _ in jobs:
            self.items[row].status = Status.WAITING
            self.items[row].message = ""
        self._render_queue()
        self.batch_total, self.batch_done = len(jobs), 0
        self.batch_counts = {}
        self.total_progress.setValue(0)
        self.worker = DownloadWorker(jobs, options, self.service)
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_result)
        self.worker.warning.connect(lambda text: self._show_notice(text, True))
        self.worker.finished.connect(self._finished)
        self.summary.setText(f"Завантажуємо · 0 із {self.batch_total}")
        self._update_controls()
        self.worker.start()

    def _on_progress(self, row: int, progress: Progress):
        self.items[row].status = progress.status
        self._set_row_status(row, progress.status)
        text = f"{progress.percent}%" if progress.percent is not None else "…"
        self.queue_table.setItem(row, 2, QTableWidgetItem(text))
        details = [f"Відео {self.batch_done + 1} із {self.batch_total}"]
        if progress.speed:
            details.append(f"{progress.speed / 1024 / 1024:.1f} МБ/с")
        if progress.eta is not None:
            details.append(f"залишилося ~{int(progress.eta)} с")
        self.summary.setText(" · ".join(details))
        self.total_progress.setValue(int((self.batch_done + (progress.percent or 0) / 100) * 100 / self.batch_total))

    def _on_result(self, row: int, result: DownloadResult):
        item = self.items[row]
        item.status, item.path, item.message = result.status, result.path, result.message
        self._set_row_status(row, result.status)
        self.queue_table.setItem(row, 2, QTableWidgetItem("100%" if result.status in {Status.DONE, Status.SKIPPED} else "—"))
        if result.title:
            self.queue_table.item(row, 0).setText(result.title)
        self.batch_done += 1
        self.batch_counts[result.status] = self.batch_counts.get(result.status, 0) + 1
        self.total_progress.setValue(int(self.batch_done * 100 / self.batch_total))
        if result.message:
            self.detail.setText(result.message)

    def _stop(self):
        if self.worker:
            self.worker.cancel()
            self.summary.setText("Зупиняємо завантаження…")
            self.stop_button.setEnabled(False)

    def _finished(self):
        stopped = self.worker.stop_event.is_set()
        self.worker.deleteLater()
        self.worker = None
        done = self.batch_counts.get(Status.DONE, 0)
        skipped = self.batch_counts.get(Status.SKIPPED, 0)
        errors = self.batch_counts.get(Status.ERROR, 0)
        self.summary.setText("Чергу зупинено" if stopped else "Чергу оброблено")
        self._show_notice(f"Завантажено: {done} · Уже були на диску: {skipped} · Помилок: {errors}", bool(errors))
        self._update_controls()
        self._refresh_history()
        if self.close_pending:
            self.close()

    def _refresh_history(self):
        try:
            self.history_rows = self.storage.history()
        except Exception as exc:
            self.history_detail.setText(f"Не вдалося прочитати історію: {exc}")
            return
        self.history_table.setRowCount(len(self.history_rows))
        for row, entry in enumerate(self.history_rows):
            when = datetime.fromisoformat(entry["created_at"]).astimezone().strftime("%d.%m.%Y  %H:%M")
            for column, value in enumerate((when, entry["title"] or entry["url"], entry["status"])):
                cell = QTableWidgetItem(value)
                cell.setToolTip(entry["message"] or entry["path"] or entry["url"])
                self.history_table.setItem(row, column, cell)
        self.history_detail.setText(f"Операцій в історії: {len(self.history_rows)}. Вибери рядок, щоб переглянути подробиці.")

    def _history_selection(self):
        row = self.history_table.currentRow()
        if 0 <= row < len(self.history_rows):
            entry = self.history_rows[row]
            self.history_detail.setText(entry["message"] or entry["path"] or entry["url"])

    def _open_path(self, path: Path | None):
        if path is None or not path.exists():
            QMessageBox.information(self, "Файл недоступний", "Файл ще не завантажено або його переміщено. Запусти завантаження повторно.")
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            QMessageBox.warning(self, "Не вдалося відкрити", f"Відкрий файл вручну:\n{path}")

    def _open_queue_file(self, row: int, column: int):
        self._open_path(self.items[row].path)

    def _history_path(self) -> Path | None:
        row = self.history_table.currentRow()
        if 0 <= row < len(self.history_rows) and self.history_rows[row]["path"]:
            return Path(self.history_rows[row]["path"])
        return None

    def _open_history_file(self):
        self._open_path(self._history_path())

    def _open_history_folder(self):
        path = self._history_path()
        self._open_path(path.parent if path else None)

    def closeEvent(self, event):
        if self.worker is not None:
            self.close_pending = True
            self._stop()
            self._show_notice("Завершуємо мережеву операцію перед закриттям вікна…")
            event.ignore()
            return
        try:
            self.storage.save_settings(self.output_input.text().strip())
        except OSError:
            pass
        event.accept()
