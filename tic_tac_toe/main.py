# -*- coding: utf-8 -*-
"""
Игра «Крестики-нолики» на Python + PyQt5.

Особенности:
  * Игровое поле 3x3 на QGridLayout, клетки — крупные QPushButton.
  * QLabel со статусом игры ("Ход: X", "Победил: O!", "Ничья").
  * Кнопка «Новая игра» для сброса партии.
  * QSS-стили: скруглённые углы, приятный фон, X — синий, O — красный.
  * Курсор «рука» (pointer) при наведении на свободную клетку.
  * Проверка всех 8 выигрышных комбинаций и ничьей.
  * После окончания игры клики блокируются до нажатия «Новая игра».
  * Выигрышная линия подсвечивается жирной рамкой и другим цветом фона.

Запуск:  python main.py
Зависимости:  pip install PyQt5
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
)

# ---------------------------------------------------------------------------
# Константы игры
# ---------------------------------------------------------------------------

EMPTY = ""      # Пустая клетка
X_MARK = "X"    # Первый игрок
O_MARK = "O"    # Второй игрок

BOARD_SIZE = 3  # Размер поля (3x3)

# Все 8 выигрышных комбинаций: 3 строки, 3 столбца, 2 диагонали.
# Каждая комбинация — кортеж из трёх индексов клеток (0..8).
WIN_LINES = (
    ((0, 1, 2), (3, 4, 5), (6, 7, 8),   # строки
     (0, 3, 6), (1, 4, 7), (2, 5, 8),   # столбцы
     (0, 4, 8), (2, 4, 6))              # диагонали
)

# ---------------------------------------------------------------------------
# Стили QSS
# ---------------------------------------------------------------------------

STYLE_SHEET = """
/* Общий фон главного окна */
QWidget#MainWindow {
    background-color: #f0f4f8;
}

/* Панель статуса */
QLabel#StatusLabel {
    font-size: 22px;
    font-weight: bold;
    color: #2d3748;
    padding: 12px;
    border-radius: 12px;
    background-color: #ffffff;
    border: 2px solid #cbd5e0;
}

/* Обычная (пустая) клетка */
QPushButton.Cell {
    background-color: #ffffff;
    border: 2px solid #cbd5e0;
    border-radius: 16px;
    font-size: 48px;
    font-weight: bold;
    color: #2d3748;
}

/* Клетка, доступная для хода — меняем фон при наведении */
QPushButton.Cell:enabled:hover {
    background-color: #e2e8f0;
    border-color: #90cdf4;
}

/* Отжатие клетки */
QPushButton.Cell:pressed {
    background-color: #cbd5e0;
}

/* Цвет крестика — синий */
QPushButton.CellX {
    color: #2b6cb0;
}

/* Цвет нолика — красный */
QPushButton.CellO {
    color: #c53030;
}

/* Заблокированная клетка после конца игры */
QPushButton.CellDisabled {
    background-color: #edf2f7;
    color: #a0aec0;
}

/* Подсветка выигрышной линии: жирная рамка и золотистый фон */
QPushButton.CellWin {
    background-color: #fefcbf;
    border: 4px solid #d69e2e;
}

/* Кнопка «Новая игра» */
QPushButton#NewGameButton {
    background-color: #3182ce;
    color: white;
    font-size: 17px;
    font-weight: bold;
    padding: 12px 24px;
    border: none;
    border-radius: 12px;
}

QPushButton#NewGameButton:hover {
    background-color: #2b6cb0;
}

QPushButton#NewGameButton:pressed {
    background-color: #2c5282;
}
"""


class TicTacToeLogic:
    """Класс с чистой игровой логикой (без привязки к GUI).

    Хранит состояние поля в плоском списке из 9 элементов и умеет
    определять победителя и ничью. Такое разделение упрощает тестирование
    и повторное использование логики (например, для бота или CLI-версии).
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Сбросить игру: пустое поле, первый ход за X."""
        self.board = [EMPTY] * (BOARD_SIZE * BOARD_SIZE)
        self.current_player = X_MARK
        self.winner = None          # Победитель: "X", "O" или None
        self.win_line = None        # Индексы выигрышной линии (кортеж)
        self.is_draw = False        # Признак ничьей
        self.is_finished = False    # Игра окончена (победа или ничья)

    def is_cell_free(self, index: int) -> bool:
        """Свободна ли клетка с указанным индексом (защита от выхода за границы)."""
        return 0 <= index < len(self.board) and self.board[index] == EMPTY

    def make_move(self, index: int) -> bool:
        """Сделать ход в клетку index.

        Возвращает True, если ход был засчитан, и False, если ход
        недопустим (игра окончена, клетка занята или индекс вне поля).
        """
        # Блокируем любые действия после завершения партии
        if self.is_finished or not self.is_cell_free(index):
            return False

        # Ставим метку текущего игрока
        self.board[index] = self.current_player

        # Проверяем, не привёл ли ход к победе
        line = self._find_win_line(self.current_player)
        if line is not None:
            self.winner = self.current_player
            self.win_line = line
            self.is_finished = True
            return True

        # Проверяем ничью: все клетки заняты, но победителя нет
        if all(cell != EMPTY for cell in self.board):
            self.is_draw = True
            self.is_finished = True
            return True

        # Ход переходит к другому игроку
        self.current_player = O_MARK if self.current_player == X_MARK else X_MARK
        return True

    def _find_win_line(self, player: str):
        """Найти первую выигрышную линию для указанного игрока или None."""
        for line in WIN_LINES:
            if all(self.board[i] == player for i in line):
                return line
        return None


class MainWindow(QWidget):
    """Главное окно приложения: собирает UI и связывает его с логикой."""

    def __init__(self, logic: TicTacToeLogic):
        super().__init__()
        self.logic = logic
        self.cells = []  # Список кнопок-клеток (индексы 0..8)

        self.setObjectName("MainWindow")
        self.setWindowTitle("Крестики-нолики")
        self.setFixedSize(420, 560)  # Фиксированный размер — поле всегда аккуратно выглядит

        self._build_ui()
        self._update_status()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_ui(self):
        """Создать виджеты и разместить их по вертикали: статус, поле, кнопка."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(16)

        # Верхняя панель — QLabel со статусом игры
        self.status_label = QLabel("Ход: X")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(self.status_label)

        # Игровое поле 3x3 на QGridLayout из кнопок QPushButton
        board_widget = QWidget()
        grid = QGridLayout(board_widget)
        grid.setSpacing(10)

        for index in range(BOARD_SIZE * BOARD_SIZE):
            button = QPushButton("")
            button.setProperty("class", "Cell")  # CSS-класс для QSS
            button.setFixedSize(120, 120)        # Крупные удобные клетки
            button.setCursor(Qt.PointingHandCursor)  # Курсор «рука»
            button.setFont(QFont("Arial", 48, QFont.Bold))
            button.setEnabled(True)

            row, col = divmod(index, BOARD_SIZE)
            grid.addWidget(button, row, col)

            # Передаём индекс клетки обработчику через default argument,
            # чтобы избежать «позднего связывания» замыкания в цикле.
            button.clicked.connect(lambda checked=False, i=index: self._on_cell_clicked(i))
            self.cells.append(button)

        root_layout.addWidget(board_widget, alignment=Qt.AlignCenter)

        # Нижняя панель — кнопка «Новая игра»
        new_game_button = QPushButton("Новая игра")
        new_game_button.setObjectName("NewGameButton")
        new_game_button.setCursor(Qt.PointingHandCursor)
        new_game_button.clicked.connect(self._on_new_game)
        root_layout.addWidget(new_game_button, alignment=Qt.AlignCenter)

    # ------------------------------------------------------------------
    # Обработчики событий
    # ------------------------------------------------------------------
    def _on_cell_clicked(self, index: int):
        """Обработка клика по клетке с защитой от исключений."""
        try:
            # Логика сама отсекает недопустимые ходы (занято/игра окончена)
            accepted = self.logic.make_move(index)
            if not accepted:
                return

            button = self.cells[index]
            player = self.logic.board[index]

            # Рисуем символ текстом, задаём цвет через динамический класс
            button.setText(player)
            button.setProperty("class", "Cell CellX" if player == X_MARK else "Cell CellO")
            button.setEnabled(False)  # Занятую клетку больше нельзя нажать

            # Если партия завершена — подсветка/блокировка и финальный статус
            if self.logic.is_finished:
                self._finish_game_ui()

            self._refresh_style(button)
            self._update_status()
        except Exception as exc:  # Любая непредвиденная ошибка не должна ронять приложение
            self._show_error(exc)

    def _on_new_game(self):
        """Полный сброс партии по кнопке «Новая игра»."""
        try:
            self.logic.reset()
            for button in self.cells:
                button.setText("")
                button.setEnabled(True)
                button.setProperty("class", "Cell")
                self._refresh_style(button)
            self._update_status()
        except Exception as exc:
            self._show_error(exc)

    # ------------------------------------------------------------------
    # Вспомогательные методы UI
    # ------------------------------------------------------------------
    def _finish_game_ui(self):
        """По завершении игры подсветить выигрышную линию и заблокировать поле."""
        if self.logic.win_line is not None:
            # Выигрышная линия: жирная рамка и золотистый фон
            for i in self.logic.win_line:
                btn = self.cells[i]
                base = "Cell CellX" if btn.text() == X_MARK else "Cell CellO"
                btn.setProperty("class", base + " CellWin")
                self._refresh_style(btn)

        # Остальные клетки визуально «гасим»
        for i, btn in enumerate(self.cells):
            if self.logic.win_line and i in self.logic.win_line:
                continue
            if btn.text():  # занятые клетки — приглушённым цветом символа
                base = "Cell CellX" if btn.text() == X_MARK else "Cell CellO"
                btn.setProperty("class", base + " CellDisabled")
            else:
                btn.setProperty("class", "Cell CellDisabled")
            btn.setEnabled(False)
            self._refresh_style(btn)

    def _refresh_style(self, widget):
        """Принудительно переприменить стиль после смены property("class").

        Без этого шага QSS-класс, заданный через setProperty, не обновляется
        «на лету» — нужно удалить и снова присвоить свойство и вызвать
        unpolish/polish.
        """
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _update_status(self):
        """Обновить текст панели статуса в соответствии с состоянием игры."""
        if self.logic.winner:
            text = f"Победил: {self.logic.winner}!"
        elif self.logic.is_draw:
            text = "Ничья"
        else:
            text = f"Ход: {self.logic.current_player}"
        self.status_label.setText(text)

    def _show_error(self, exc: Exception):
        """Показать некритичное окно с описанием внутренней ошибки."""
        QMessageBox.critical(self, "Ошибка", f"Произошла внутренняя ошибка:\n{exc}")


def main():
    """Точка входа: создаёт приложение, окно и запускает цикл событий."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Единый базовый стиль — QSS выглядит предсказуемо
    app.setStyleSheet(STYLE_SHEET)

    window = MainWindow(TicTacToeLogic())
    window.show()

    # sys.exit гарантирует корректное завершение процесса с кодом цикла событий
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
