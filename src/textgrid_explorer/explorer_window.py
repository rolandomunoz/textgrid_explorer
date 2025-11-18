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
import re
import shutil
import subprocess
from importlib import resources

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QMessageBox,
    QTableView,
    QMenuBar,
    QToolBar,
    QVBoxLayout,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    Slot,
    QSettings,
    QRegularExpression,
    QItemSelectionRange,
    QSortFilterProxyModel,
)
from PySide6.QtGui import (
    QPixmap,
    QAction,
    QIcon,
)

from textgrid_explorer.models import TGTableModel
from textgrid_explorer.dialogs import NewProjectDialog
from textgrid_explorer.dialogs import FilterByDialog
from textgrid_explorer.dialogs import FindAndReplaceDialog
from textgrid_explorer.dialogs import MapAnnotationDialog
from textgrid_explorer.dialogs import PreferencesDialog
from textgrid_explorer.resources import rc_icons
from textgrid_explorer import utils

resources_dir = resources.files('textgrid_explorer.resources')
settings = QSettings('Gilgamesh', 'textgrid_explorer')

class EditorView(QWidget):
    save_changes = Signal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()
        self._modified_indexes = set()

    def init_ui(self):
        self.table_view = QTableView()

        model = TGTableModel()
        model.dataChanged.connect(self.on_changed_indexes)
        proxy_model = QSortFilterProxyModel(model)
        proxy_model.setSourceModel(model)
        self.table_view.setModel(proxy_model)

        box_layout = QVBoxLayout()
        box_layout.addWidget(self.table_view)
        self.setLayout(box_layout)

    def on_changed_indexes(self, topleft, bottomright, roles):
        if not topleft.isValid() or not topleft.isValid():
            return
        selection_range = QItemSelectionRange(topleft, bottomright)
        indexes = selection_range.indexes()
        for index in indexes:
            self._modified_indexes.add(index)
        self.save_changes.emit(True)

    def set_table_data(self, headers, data):
        """
        Set the table data.

        Parameters
        ----------
        headers : list of str
            Column names.
        data : list of list
            The inner list have n-dimensions and the first element is a `pathlib.Path`
            and the rest of the elements are `mytextgrid.core.interval_tier.Interval` or None.
        """
        model = self.table_view.model().sourceModel()
        model.set_full_dataset(headers, data)

    def model(self):
        return self.table_view.model()

    def modified_indexes(self):
        """
        QModelIndex objects corresponding to all modified (unsaved) data
        cells in the model
        """
        return self._modified_indexes

    def clear_modified_indexes(self):
        """
        Clear the internal list of modified indexes, typically called after
        a successful save operation.
        """
        self._modified_indexes.clear()
        self.save_changes.emit(False)

class TGExplorer(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('TextGrid Explorer')
        self.setMinimumSize(800, 500)
        #self.showMaximized()
        self.create_dialogs()
        self.create_actions()
        self.init_ui()
        self.create_menubar()
        self.create_toolbar()
        self.on_enabled_buttons(False)

    def create_actions(self):
        """
        Create actions
        """
        # File
        self.new_project_act = QAction(self.tr('&New project...'), self)
        self.new_project_act.setShortcut('Ctrl+N')
        self.new_project_act.triggered.connect(self.new_project_dlg.open)

        self.open_project_act = QAction(self.tr('&Open project...'), self)
        self.open_project_act.setShortcut('Ctrl+O')
        self.open_project_act.triggered.connect(self.on_open_project)

        self.close_project_act = QAction(self.tr('&Close project'), self)
        self.close_project_act.triggered.connect(self.on_close_project)

        self.project_settings_act = QAction(self.tr('&Project settings...'), self)
        self.project_settings_act.setShortcut('Ctrl+R')
        self.project_settings_act.triggered.connect(self.on_project_settings)

        save_icon = QIcon(QPixmap(':icons/disk.png'))
        self.save_changes_act = QAction(save_icon, self.tr('&Save Changes'), self)
        self.save_changes_act.setShortcut('Ctrl+S')
        self.save_changes_act.triggered.connect(self.on_save_changes)

        self.quit_act = QAction(self.tr('&Quit'), self)
        self.quit_act.setShortcut('Ctrl+Q')
        self.quit_act.triggered.connect(self.close)

        # Data
        self.sort_az_act = QAction(self.tr('Sort table by column (A to Z)'), self)
        self.sort_az_act.triggered.connect(self.on_sort_az)

        self.sort_za_act = QAction(self.tr('Sort table by column (Z to A)'), self)
        self.sort_za_act.triggered.connect(self.on_sort_za)

        funnel_icon = QIcon(QPixmap(':icons/funnel.png'))
        self.filter_act = QAction(funnel_icon, self.tr('&Filter by...'), self)
        self.filter_act.triggered.connect(self.popup_filter_dlg)

        praat_icon = QIcon(QPixmap(':icons/praat_icon.png'))
        self.open_praat_act = QAction(praat_icon, self.tr('&Open selection in Praat'), self)
        self.open_praat_act.triggered.connect(self.on_open_praat)
        self.open_praat_act.setShortcut('Alt+P')

        # Edit
        self.find_and_replace_act = QAction(self.tr('&Find and replace...'), self)
        self.find_and_replace_act.setShortcut('Ctrl+H')
        self.find_and_replace_act.triggered.connect(lambda: self.popup_find_and_replace_dlg(1))

        self.find_act = QAction(self.tr('&Find...'), self)
        self.find_act.setShortcut('Ctrl+F')
        self.find_act.triggered.connect(lambda: self.popup_find_and_replace_dlg(0))

        self.map_annotation_act = QAction(self.tr('&Map annotation...'), self)
        self.map_annotation_act.triggered.connect(self.popup_map_annotation_dlg)

        self.preferences_act = QAction(self.tr('&Preferences...'), self)
        self.preferences_act.triggered.connect(self.popup_preferences_dlg)

    def create_menubar(self):
        menu_bar = QMenuBar()

        file_bar = menu_bar.addMenu(self.tr('&File'))
        file_bar.addAction(self.new_project_act)
        file_bar.addAction(self.open_project_act)
        file_bar.addAction(self.close_project_act)
        file_bar.addSeparator()
        file_bar.addAction(self.project_settings_act)
        file_bar.addSeparator()
        file_bar.addAction(self.save_changes_act)
        file_bar.addSeparator()
        file_bar.addAction(self.quit_act)

        edit_bar = menu_bar.addMenu(self.tr('&Edit'))
        edit_bar.addAction(self.find_and_replace_act)
        edit_bar.addAction(self.find_act)
        edit_bar.addAction(self.map_annotation_act)
        edit_bar.addSeparator()
        edit_bar.addAction(self.open_praat_act)
        edit_bar.addSeparator()
        edit_bar.addAction(self.preferences_act)

        data_bar = menu_bar.addMenu(self.tr('&View'))
        data_bar.addAction(self.sort_az_act)
        data_bar.addAction(self.sort_za_act)
        data_bar.addSeparator()
        data_bar.addAction(self.filter_act)

        self.setMenuBar(menu_bar)

    def create_toolbar(self):
        data_toolbar = QToolBar(self)
        data_toolbar.addAction(self.save_changes_act)
        data_toolbar.addAction(self.open_praat_act)
        data_toolbar.addAction(self.filter_act)

        self.addToolBar(data_toolbar)

    def init_ui(self):
        self.editor_view = EditorView(self)
        self.editor_view.save_changes.connect(self.save_changes_act.setEnabled)
        selection_model = self.editor_view.table_view.selectionModel()
        selection_model.currentColumnChanged.connect(self.on_sorting_act)
        self.setCentralWidget(self.editor_view)

    def create_dialogs(self):
        self.preferences_dlg = PreferencesDialog(self)
        self.preferences_dlg.accepted.connect(self.on_preferences)

        self.new_project_dlg = NewProjectDialog(self)
        self.new_project_dlg.accepted.connect(self.on_load_data)

        self.simple_filter_dlg = FilterByDialog(self)
        self.simple_filter_dlg.filtered_by.connect(self.on_filter_rows)

        self.find_and_replace_dlg = FindAndReplaceDialog(self)
        self.find_and_replace_dlg.replace_all_clicked.connect(self.on_replace_all)
        self.find_and_replace_dlg.replace_clicked.connect(self.on_replace)
        self.find_and_replace_dlg.find_all_clicked.connect(self.on_find_all)
        self.find_and_replace_dlg.find_clicked.connect(lambda: self.on_find(1))

        self.map_annotations_dlg = MapAnnotationDialog(self)
        self.map_annotations_dlg.accepted.connect(self.on_map_annotations)

    def closeEvent(self, e):
        indexes = self.editor_view.modified_indexes()
        if indexes:
            response = QMessageBox.question(
                self,
                'Save Changes?',
                'You have unsaved changes. Do you want to save them before quitting?'
            )
            if response == QMessageBox.StandardButton.Yes:
                self.on_save_changes()
        super().closeEvent(e)

    def popup_preferences_dlg(self):
        praat_path = settings.value('praat_path')
        praat_sound_extensions = settings.value('praat_sound_extensions')
        praat_maximize_audibility = settings.value('praat_maximize_audibility')
        praat_activate_plugins = settings.value('praat_activate_plugins')

        self.preferences_dlg.set_values(
            praat_path,
            praat_sound_extensions,
            bool(int(praat_maximize_audibility)),
            bool(int(praat_activate_plugins)),
        )
        self.preferences_dlg.open()

    def popup_filter_dlg(self):
        proxy_model = self.editor_view.table_view.model()
        ncols = proxy_model.columnCount()
        orientation = Qt.Orientation.Horizontal
        fields = [proxy_model.headerData(i, orientation) for i in range(ncols)]

        self.simple_filter_dlg.set_fields(fields)
        index = self.editor_view.table_view.selectionModel().currentIndex()
        if index.isValid():
            column_index = index.column()
            self.simple_filter_dlg.set_index_field(column_index)
        self.simple_filter_dlg.show()

    def popup_find_and_replace_dlg(self, tab_index=0):
        column_index = -1
        column_names = []
        find_pattern = ''

        # Get column names
        model = self.editor_view.table_view.model()
        for i in range(model.columnCount()):
            column_names.append(
                model.headerData(i, Qt.Orientation.Horizontal)
            )

        # On selection
        indexes = self.editor_view.table_view.selectedIndexes()
        if indexes:
            index = indexes[0] #topleft selection
            column_index = index.column()

            if len(indexes) == 1: # If selected on cell
                find_pattern = index.data()

        ## Fill up find tab
        self.find_and_replace_dlg.set_column_field(column_names, column_index)
        self.find_and_replace_dlg.set_find_field(find_pattern)

        ## Fill up replace tab
        self.find_and_replace_dlg.display_tab(tab_index)
        self.find_and_replace_dlg.show()

    def popup_map_annotation_dlg(self):
        """
        Prepare and show non-modal dialog.
        """
        proxy_model = self.editor_view.table_view.model()
        ncols = proxy_model.columnCount()
        orientation = Qt.Orientation.Horizontal
        fields = [proxy_model.headerData(i, orientation) for i in range(ncols)]

        self.map_annotations_dlg.set_fields(fields)
        self.map_annotations_dlg.show()

    def on_find(self, step=1):
        """
        Find the next item in the specified column starting from the
        selected row.
        """
        table_view = self.editor_view.table_view
        proxy_model = table_view.model()
        source_model = proxy_model.sourceModel()

        # 1. From the QDialog, get the column index and the search pattern
        dlg_dict = self.find_and_replace_dlg.data()
        col_ind = dlg_dict['column_index']
        pattern = dlg_dict['pattern']

        # 2. From the QTableView, get the current selected row
        row_ind = 0
        proxy_indexes = table_view.selectedIndexes()
        if proxy_indexes:
            current_source_index = proxy_model.mapToSource(proxy_indexes[0])
            row_ind = current_source_index.row() + step

        # 3. Find the next item moving on from the current selected row,
        # the specified column and the pattern
        p = re.compile(pattern)
        for i in range(row_ind, source_model.rowCount()):
            source_index = source_model.index(i, col_ind)
            cell_text = source_index.data()
            if not p.search(cell_text):
                continue

            proxy_index = proxy_model.mapFromSource(source_index)
            if not proxy_index.isValid():
                continue

            sel_model = table_view.selectionModel()
            sel_model.select(proxy_index, sel_model.SelectionFlag.ClearAndSelect)
            table_view.setCurrentIndex(proxy_index) # Focus
            table_view.scrollTo(proxy_index)
            return True
        return False

    def on_find_all(self):
        print('Find All')

    def on_replace(self):
        """
        Replace the items, one by one, that match a pattern in the
        QTableView.
        """
        table_view = self.editor_view.table_view

        # 1. Use the find to match a value
        match = self.on_find(0)

        if not match:
            return False

        # 2. From the QDialog, get the column index, the search pattern
        #    and the replace
        dlg_dict = self.find_and_replace_dlg.data()
        col_ind = dlg_dict['column_index']
        pattern = dlg_dict['pattern']
        repl = dlg_dict['replace']

        # 3. Once match is found, replace the item
        proxy_model = table_view.model()
        proxy_indexes = table_view.selectedIndexes()
        if not proxy_indexes:
            return False

        proxy_index = proxy_indexes[0]
        source_index = proxy_model.mapToSource(proxy_index)

        source_model = proxy_model.sourceModel()
        source_model.replace([source_index], pattern, repl)
        return True

    def on_replace_all(self):
        """
        Replace all items in the specified column that match a pattern.
        """
        table_view = self.editor_view.table_view

        # 1. From the QDialog, get the column index, the search pattern
        #    and the replace
        dlg_dict = self.find_and_replace_dlg.data()
        col_ind = dlg_dict['column_index']
        pattern = dlg_dict['pattern']
        repl = dlg_dict['replace']

        # 2. Get the all the indexes from the selected column
        proxy_model = table_view.model()
        source_model = proxy_model.sourceModel()

        source_indexes = []
        for i in range(proxy_model.rowCount()):
            proxy_item = proxy_model.index(i, col_ind)
            source_item = proxy_model.mapToSource(proxy_item)
            if not source_item.isValid():
                continue
            source_indexes.append(source_item)

        # 3. Replace All
        source_model.replace(source_indexes, pattern, repl)
        return True

    def on_map_annotations(self):
        r = self.map_annotations_dlg.data()

        proxy_model = self.editor_view.table_view.model()
        model = proxy_model.sourceModel()
        model.replace_all(
            r.find, r.replace, r.src_column_index, r.dst_column_index,
        )

    def on_open_praat(self):
        table_view = self.editor_view.table_view
        indexes = table_view.selectedIndexes()
        if not indexes:
            return

        index = indexes[0]

        if not index.isValid():
            return

        if index.column() == 0:
            return

        item = index.data(Qt.ItemDataRole.UserRole)
        if item is None:
            return

        sound_extensions = settings.value('praat_sound_extensions').split(';')
        sound_path = ''
        textgrid_path = item.textgrid().file_path
        for sound_ext in sound_extensions:
            sound_path_tmp = textgrid_path.with_suffix(sound_ext)
            if sound_path_tmp.is_file():
                sound_path = sound_path_tmp
                break

        praat_path_ = settings.value('praat_path')
        praat_path = shutil.which(praat_path_)
        if praat_path is None:
            QMessageBox.critical(
                self,
                'Open selection in Praat',
                'It seems like the <b>Praat path</b> does not exist. Please, go to <b>Edit > Preferences</br'
            )

        maximize_audibility = settings.value('praat_maximize_audibility')
        maximize_audibility = int(maximize_audibility)

        activate_plugins = settings.value('praat_activate_plugins') # On Linux it is a str'
        activate_plugins = bool(int(activate_plugins))

        script_path = resources_dir / 'open_file.praat'
        args = [
            praat_path,
            '--hide-picture',
            '--no-plugins',
            '--new-send',
            script_path,
            textgrid_path,
            sound_path,
            str(maximize_audibility),
            str(item.tier().index + 1),
            str(item.xmin),
            str(item.xmax)
        ]

        if activate_plugins:
            args.pop(2) # Remove --no-plugins
        subprocess.run(args)

    def on_enabled_buttons(self, b):
        self.save_changes_act.setEnabled(b)
        self.close_project_act.setEnabled(b)
        self.project_settings_act.setEnabled(b)
        self.open_project_act.setEnabled(b)
        self.open_praat_act.setEnabled(b)
        self.filter_act.setEnabled(b)
        self.find_and_replace_act.setEnabled(b)
        self.find_act.setEnabled(b)
        self.map_annotation_act.setEnabled(b)
        self.sort_az_act.setEnabled(b)
        self.sort_za_act.setEnabled(b)

    def on_open_project(self):
        pass

    def on_project_settings(self):
        pass

    def on_close_project(self):
        indexes = self.editor_view.modified_indexes()
        if indexes:
            response = QMessageBox.question(
                self,
                'Save Changes?',
                'You have unsaved changes. Do you want to save them before closing the project?'
            )
            if response == QMessageBox.StandardButton.Yes:
                self.on_save_changes()

        self.editor_view.set_table_data([], [])
        self.on_enabled_buttons(False)
        self.editor_view.clear_modified_indexes()

    def on_load_data(self):
        # Get variables from a dialog
        dict_ = self.new_project_dlg.data()

        src_dir = dict_['src_dir']

        primary_tier = dict_['primary_tier']
        if primary_tier is None:
            primary_tier = []

        secondary_tiers = dict_['secondary_tiers']
        if secondary_tiers is None:
            secondary_tiers = []

        # Build table headers and data
        headers, data = utils.create_aligned_tier_table(
            src_dir, primary_tier, secondary_tiers
        )

        # Fill up table
        self.editor_view.set_table_data(headers, data)

        # Enable buttons
        self.on_enabled_buttons(True)
        self.save_changes_act.setEnabled(False)

    @Slot(dict)
    def on_filter_rows(self, dict_):
        proxy_model = self.editor_view.model()
        if dict_['is_regular_expression']:
            regex_pattern = QRegularExpression(dict_['pattern'])
            if not regex_pattern.isValid():
                return
            proxy_model.setFilterKeyColumn(dict_['column_index'])
            proxy_model.setFilterRegularExpression(dict_['pattern'])
        else:
            proxy_model.setFilterKeyColumn(dict_['column_index'])
            proxy_model.setFilterFixedString(dict_['pattern'])

    def on_sort_az(self):
        table_view = self.editor_view.table_view
        indexes = table_view.selectedIndexes()
        if indexes:
            topleft_index = indexes[0]
            column_index = topleft_index.column()
            table_view.sortByColumn(column_index, Qt.SortOrder.AscendingOrder)

    def on_sort_za(self):
        table_view = self.editor_view.table_view
        indexes = table_view.selectedIndexes()
        if indexes:
            topleft_index = indexes[0]
            column_index = topleft_index.column()
            table_view.sortByColumn(column_index, Qt.SortOrder.DescendingOrder)

    def on_sorting_act(self, current_index, previous_index):
        """
        Update the name of the `Sort by column (A to Z)` command with the
        selected column name.
        """
        if not current_index.isValid():
            return
        column_index = current_index.column()
        column_name = current_index.model().headerData(column_index, Qt.Orientation.Horizontal)
        self.sort_az_act.setText(f'Sort by column "{column_name}" (A to Z)')
        self.sort_za_act.setText(f'Sort by column "{column_name}" (Z to A)')

    def on_save_changes(self):
        tmp_paths = set()
        indexes = self.editor_view.modified_indexes()
        for index in indexes:
            src_model = index.model()
            src_model.setData(index, False, Qt.ItemDataRole.ForegroundRole)

            item = index.data(Qt.ItemDataRole.UserRole)
            textgrid = item.textgrid()
            if textgrid.file_path in tmp_paths:
                continue
            textgrid.write(textgrid.file_path) #Save path
            tmp_paths.add(textgrid.file_path)
        self.editor_view.clear_modified_indexes()

    def on_preferences(self):
        dict_ = self.preferences_dlg.to_dict()

        # Normalize extensions input
        ext_pattern = re.compile(r'\.?[a-zA-Z0-9]+')
        ext_list = dict_['praat_sound_extensions'].split(';')
        norm_ext_list = []
        for sound_ext in ext_list:
            sound_ext = sound_ext.strip()
            if not ext_pattern.match(sound_ext):
                continue
            sound_ext = sound_ext if sound_ext.startswith('.') else f'.{sound_ext}'
            if sound_ext in norm_ext_list:
                continue
            norm_ext_list.append(sound_ext)
        extensions_str = ';'.join(norm_ext_list)

        settings.setValue('praat_path', dict_['praat_path'])
        settings.setValue('praat_sound_extensions', extensions_str)
        settings.setValue('praat_maximize_audibility', int(dict_['praat_maximize_audibility']))
        settings.setValue('praat_activate_plugins', int(dict_['praat_activate_plugins']))
