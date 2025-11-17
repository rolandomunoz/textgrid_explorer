#!/usr/bin/env python
#   textgrid_explorer - A TextGrid editing tool with a spreadsheet interface
#   Copyright (C) 2025 Rolando Muñoz <rolando.muar@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License version 3, as published
#   by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranties of
#   MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program.  If not, see <https://www.gnu.org/licenses/>.
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import (
    Qt,
    Signal,
)

class FilterByDialog(QDialog):
    filtered_by = Signal(dict)

    def __init__(self, parent, fields=None, default_value=''):
        super().__init__(parent)
        self._fields = fields
        self.default_value = default_value
        if fields is None:
            self._fields = []
        self.setWindowTitle('Filter by')
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        # Headers
        self.headers_box = QComboBox(self)
        self.headers_box.addItems(self._fields)
        self.headers_box.currentIndexChanged.connect(self.on_changed)

        self.line_ed = QLineEdit(self.default_value, self)
        #self.line_ed.setPlaceholderText('Regex expression')
        self.line_ed.textChanged.connect(self.on_changed)

        self.regex_checkbox = QCheckBox('Regular Expressions')
        self.regex_checkbox.checkStateChanged.connect(self.on_changed)

        # Buttons
        clear_btn = QPushButton('C&lear', self)
        clear_btn.clicked.connect(self.on_clear)

        cancel_btn = QPushButton('&Close', self)
        cancel_btn.clicked.connect(self.reject)

        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(clear_btn)
        hbox.addWidget(cancel_btn)

        options_box = QVBoxLayout()
        options_box.addWidget(self.regex_checkbox)
        other_options_groupbox = QGroupBox('Other options')
        other_options_groupbox.setLayout(options_box)

        # Main Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Select column:'))
        layout.addWidget(self.headers_box)
        layout.addWidget(QLabel('Search pattern:'))
        layout.addWidget(self.line_ed)
        layout.addWidget(other_options_groupbox)
        layout.addLayout(hbox)

        self.setLayout(layout)

    def on_changed(self):
        dict_ = self.to_dict()
        self.filtered_by.emit(dict_)

    def on_clear(self):
        self.line_ed.setText('')

    def fields(self):
        return self._fields

    def set_fields(self, fields):
        if not self._fields == fields:
            self._fields = fields
            self.headers_box.clear()
            self.headers_box.addItems(self._fields)

    def set_index_field(self, index: int) -> None:
        self.headers_box.setCurrentIndex(index)

    def to_dict(self):
        dict_ = {
            'column_index': self.headers_box.currentIndex(),
            'column_name': self.headers_box.currentText(),
            'pattern': self.line_ed.text(),
            'is_regular_expression': self.regex_checkbox.isChecked(),
        }
        return dict_
