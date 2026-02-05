import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QLineEdit, QPushButton, QLabel, QTextEdit, QFileDialog,
    QSplitter, QStatusBar, QMenuBar, QMenu, QProgressDialog, QHeaderView,
    QFileIconProvider, QListWidget
)
from PySide6.QtCore import Qt, QFileInfo, QDateTime
from PySide6.QtGui import QAction, QIcon
from db import DatabaseManager
from scanner import FileScanner

class MetaFolderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MetaFolder")
        self.setGeometry(100, 100, 1000, 700)
        
        # 初始化变量
        self.root_dir = None
        self.db_manager = None
        self.scanner = None
        self.current_path = "."
        self.is_searching = False
        self.search_results = []
        self.icon_provider = QFileIconProvider()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建搜索栏
        search_layout = QHBoxLayout()
        self.toggle_sidebar_btn = QPushButton("☰")
        self.toggle_sidebar_btn.setToolTip("显示/隐藏侧边栏")
        self.toggle_sidebar_btn.setFixedWidth(40)
        self.toggle_sidebar_btn.clicked.connect(self.toggle_sidebar)
        search_layout.addWidget(self.toggle_sidebar_btn)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索: 直接输入文件名, t:标签, d:备注")
        self.search_input.textChanged.connect(self.handle_search)
        search_layout.addWidget(self.search_input)
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_files)
        search_layout.addWidget(self.refresh_button)
        main_layout.addLayout(search_layout)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 创建文件列表 (QTreeWidget)
        self.file_list = QTreeWidget()
        self.file_list.setHeaderLabels(["名称", "大小", "修改日期", "类型"])
        self.file_list.setColumnWidth(0, 400)
        self.file_list.setColumnWidth(1, 100)
        self.file_list.setColumnWidth(2, 150)
        self.file_list.itemDoubleClicked.connect(self.handle_item_double_click)
        self.file_list.currentItemChanged.connect(self.handle_item_selection)
        self.splitter.addWidget(self.file_list)
        
        # 创建侧边栏
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # 标签管理
        tag_group = QWidget()
        tag_layout = QVBoxLayout(tag_group)
        tag_layout.addWidget(QLabel("标签:"))
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入标签并回车添加")
        self.tag_input.returnPressed.connect(self.add_tag)
        tag_layout.addWidget(self.tag_input)
        # 使用QListWidget显示标签
        self.tag_list = QListWidget()
        tag_layout.addWidget(self.tag_list)
        self.remove_tag_button = QPushButton("移除选中标签")
        self.remove_tag_button.clicked.connect(self.remove_tag)
        tag_layout.addWidget(self.remove_tag_button)
        sidebar_layout.addWidget(tag_group)
        
        # 备注管理
        note_group = QWidget()
        note_layout = QVBoxLayout(note_group)
        note_layout.addWidget(QLabel("备注:"))
        self.note_edit = QTextEdit()
        self.note_edit.textChanged.connect(self.update_note)
        note_layout.addWidget(self.note_edit)
        sidebar_layout.addWidget(note_group)
        
        self.splitter.addWidget(self.sidebar)
        self.splitter.setSizes([700, 300])
        main_layout.addWidget(self.splitter)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 显示欢迎信息
        self.show_welcome_message()

        # 应用样式
        self.apply_styles()
    
    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder_path:
            return
        
        self.root_dir = Path(folder_path)
        db_path = self.root_dir / "metadata.db"
        
        # 初始化数据库
        self.db_manager = DatabaseManager(str(db_path))
        
        # 初始化文件扫描器
        self.scanner = FileScanner(self.root_dir, self.db_manager)
        
        # 检查根目录是否已扫描
        if not self.db_manager.is_folder_scanned("."):
            # 定义进度回调函数
            def progress_callback(current, total, status):
                if total > 0:
                    percentage = int((current / total) * 100)
                    self.status_bar.showMessage(f"扫描中: {current}/{total} ({percentage}%) - {status}")
                QApplication.processEvents()  # 处理事件，保持界面响应
            
            # 只扫描根目录下一层
            self.scanner.scan_current_level(".", progress_callback)
            
            # 添加到已扫描文件夹数据库
            self.db_manager.add_scanned_folder(".")
            
            # 显示完成消息
            self.status_bar.showMessage("扫描完成", 2000)
        else:
            # 根目录已扫描，直接显示文件列表
            self.status_bar.showMessage("根目录已扫描，直接加载", 2000)
        
        # 显示根目录文件
        self.current_path = "."
        self.update_file_list()
        
        # 更新窗口标题
        self.setWindowTitle(f"MetaFolder - {self.root_dir.name}")
    
    def create_menu_bar(self):
        menu_bar = QMenuBar()
        self.setMenuBar(menu_bar)
        
        # 文件菜单
        file_menu = QMenu("文件", self)
        menu_bar.addMenu(file_menu)
        
        open_action = QAction("打开文件夹", self)
        open_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def show_welcome_message(self):
        self.file_list.clear()
        welcome_item = QTreeWidgetItem(["欢迎使用 MetaFolder"])
        # welcome_item.setFlags(Qt.NoItemFlags) # QTreeWidget item flags work differently
        self.file_list.addTopLevelItem(welcome_item)
        instruction_item = QTreeWidgetItem(["请从菜单中选择 '文件' -> '打开文件夹' 开始"])
        # instruction_item.setFlags(Qt.NoItemFlags)
        self.file_list.addTopLevelItem(instruction_item)
    
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def update_file_list(self):
        self.file_list.clear()
        
        # 添加返回上一级的项目
        if self.current_path != ".":
            back_item = QTreeWidgetItem(["..", "", "", ""])
            back_item.setData(0, Qt.UserRole, "..")
            # Set parent folder icon
            back_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.Folder))
            self.file_list.addTopLevelItem(back_item)
        
        # 获取当前目录下的文件和文件夹
        if not self.is_searching:
            entries = self.db_manager.get_entries_by_path_prefix(self.current_path)
        else:
            entries = self.search_results
        
        for relative_path, entry_type, description in entries:
            name = os.path.basename(relative_path)

            # 获取文件信息 (大小, 日期)
            size_str = ""
            date_str = ""
            type_str = "文件" if entry_type == "file" else "文件夹"
            icon = QIcon()

            if self.scanner:
                abs_path = self.scanner.get_absolute_path(relative_path)
                file_info = QFileInfo(abs_path)

                # 获取图标
                icon = self.icon_provider.icon(file_info)

                if file_info.exists():
                    # 获取日期
                    date_str = file_info.lastModified().toString("yyyy-MM-dd HH:mm")

                    # 获取大小
                    if entry_type == "file":
                        size_str = self.format_size(file_info.size())

                    # 修正类型显示 (如果需要更详细的类型)
                    # type_str = "文件夹" if file_info.isDir() else "文件"

            item = QTreeWidgetItem([name, size_str, date_str, type_str])
            item.setIcon(0, icon)
            item.setData(0, Qt.UserRole, relative_path)
            item.setData(0, Qt.UserRole + 1, entry_type)

            self.file_list.addTopLevelItem(item)
    
    def handle_item_double_click(self, item, column):
        if not self.root_dir:
            return
        
        relative_path = item.data(0, Qt.UserRole)
        if not relative_path:
            return
        
        # 处理返回上一级
        if relative_path == "..":
            if self.current_path != ".":
                self.current_path = str(Path(self.current_path).parent)
                if self.current_path == "":
                    self.current_path = "."
                self.update_file_list()
            return
        
        # 获取条目类型
        entry_type = item.data(0, Qt.UserRole + 1)
        if entry_type == "folder":
            # 检查是否已经扫描过该文件夹
            if not self.db_manager.is_folder_scanned(relative_path):
                # 定义进度回调函数
                def progress_callback(current, total, status):
                    if total > 0:
                        percentage = int((current / total) * 100)
                        self.status_bar.showMessage(f"扫描中: {current}/{total} ({percentage}%) - {status}")
                    QApplication.processEvents()  # 处理事件，保持界面响应
                
                # 进入文件夹前，先扫描该文件夹的下一层
                self.scanner.scan_current_level(relative_path, progress_callback)
                
                # 添加到已扫描文件夹数据库
                self.db_manager.add_scanned_folder(relative_path)
                
                # 显示完成消息
                self.status_bar.showMessage("扫描完成", 2000)
            else:
                # 文件夹已扫描，直接进入
                self.status_bar.showMessage("文件夹已扫描，直接加载", 2000)
            
            # 进入文件夹
            self.current_path = relative_path
            self.update_file_list()
        elif entry_type == "file":
            # 打开文件
            absolute_path = self.scanner.get_absolute_path(relative_path)
            os.startfile(absolute_path)
    
    def handle_item_selection(self, current, previous):
        if not current or not self.root_dir:
            return
        
        relative_path = current.data(0, Qt.UserRole)
        if not relative_path or relative_path == "..":
            # 清空标签和备注
            self.tag_list.clear()
            # 暂时断开信号连接，避免递归调用
            try:
                self.note_edit.textChanged.disconnect(self.update_note)
            except:
                pass # 可能没有连接
            self.note_edit.clear()
            # 重新连接信号
            self.note_edit.textChanged.connect(self.update_note)
            self.status_bar.showMessage("")
            return
        
        # 获取标签
        tags = self.db_manager.get_tags_for_entry(relative_path)
        self.tag_list.clear()
        for tag in tags:
            self.tag_list.addItem(tag)
        
        # 获取备注
        entry = self.db_manager.get_entry(relative_path)
        if entry:
            description = entry[2] if entry[2] else ""
            # 暂时断开信号连接，避免递归调用
            try:
                self.note_edit.textChanged.disconnect(self.update_note)
            except:
                pass
            self.note_edit.setText(description)
            # 重新连接信号
            self.note_edit.textChanged.connect(self.update_note)
        else:
            try:
                self.note_edit.textChanged.disconnect(self.update_note)
            except:
                pass
            self.note_edit.clear()
            self.note_edit.textChanged.connect(self.update_note)
        
        # 更新状态栏
        status_text = f"路径: {relative_path}"
        if tags:
            status_text += f" | 标签: {', '.join(tags)}"
        if description:
            status_text += f" | 备注: {description[:50]}..." if len(description) > 50 else f" | 备注: {description}"
        self.status_bar.showMessage(status_text)
    
    def add_tag(self):
        tag_name = self.tag_input.text().strip()
        if not tag_name:
            return
        
        # 获取当前选中的项目
        current_item = self.file_list.currentItem()
        if not current_item:
            return
        
        relative_path = current_item.data(0, Qt.UserRole)
        if not relative_path or relative_path == "..":
            return
        
        # 添加标签
        self.db_manager.add_tag_to_entry(relative_path, tag_name)
        
        # 更新标签列表
        tags = self.db_manager.get_tags_for_entry(relative_path)
        self.tag_list.clear()
        for tag in tags:
            self.tag_list.addItem(tag)
        
        # 清空标签输入
        self.tag_input.clear()
        
        # 更新状态栏
        self.handle_item_selection(current_item, None)
    
    def remove_tag(self):
        # 获取当前选中的标签
        current_tag_item = self.tag_list.currentItem()
        if not current_tag_item:
            return
        
        # 获取当前选中的文件/文件夹
        current_item = self.file_list.currentItem()
        if not current_item:
            return
        
        tag_name = current_tag_item.text()
        relative_path = current_item.data(0, Qt.UserRole)
        if not relative_path or relative_path == "..":
            return
        
        # 移除标签
        self.db_manager.remove_tag_from_entry(relative_path, tag_name)
        
        # 更新标签列表
        tags = self.db_manager.get_tags_for_entry(relative_path)
        self.tag_list.clear()
        for tag in tags:
            self.tag_list.addItem(tag)
        
        # 更新状态栏
        self.handle_item_selection(current_item, None)
    
    def update_note(self):
        # 获取当前选中的项目
        current_item = self.file_list.currentItem()
        if not current_item:
            return
        
        relative_path = current_item.data(0, Qt.UserRole)
        if not relative_path or relative_path == "..":
            return
        
        # 更新备注
        description = self.note_edit.toPlainText()
        self.db_manager.update_entry(relative_path, description)
        
        # 直接更新状态栏，避免调用handle_item_selection导致光标位置重置
        tags = self.db_manager.get_tags_for_entry(relative_path)
        status_text = f"路径: {relative_path}"
        if tags:
            status_text += f" | 标签: {', '.join(tags)}"
        if description:
            status_text += f" | 备注: {description[:50]}..." if len(description) > 50 else f" | 备注: {description}"
        self.status_bar.showMessage(status_text)
    
    def handle_search(self, text):
        if not self.root_dir:
            return
        
        text = text.strip()
        if not text:
            self.is_searching = False
            self.update_file_list()
            return
        
        # 解析搜索命令
        if text.startswith("t:"):
            # 按标签搜索
            tag_query = text[2:].strip()
            self.search_results = self.db_manager.search_entries(tag_query, "tag")
        elif text.startswith("d:"):
            # 按备注搜索
            desc_query = text[2:].strip()
            self.search_results = self.db_manager.search_entries(desc_query, "description")
        else:
            # 按文件名搜索
            self.search_results = self.db_manager.search_entries(text, "name")
        
        self.is_searching = True
        self.update_file_list()
    
    def refresh_files(self):
        if not self.root_dir:
            return
        
        # 定义进度回调函数
        def progress_callback(current, total, status):
            if total > 0:
                percentage = int((current / total) * 100)
                self.status_bar.showMessage(f"刷新中: {current}/{total} ({percentage}%) - {status}")
            QApplication.processEvents()  # 处理事件，保持界面响应
        
        # 重新扫描当前目录
        self.scanner.scan_current_level(self.current_path, progress_callback)
        
        # 从数据库中移除当前目录，以便下次进入时重新扫描
        self.db_manager.remove_scanned_folder(self.current_path)
        
        # 更新文件列表
        self.update_file_list()
        
        # 显示刷新成功消息
        self.status_bar.showMessage("文件列表已刷新", 2000)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 14px;
            }
            QTreeWidget, QListWidget {
                border: 1px solid #dcdcdc;
                background-color: white;
                border-radius: 4px;
                outline: 0;
            }
            QTreeWidget::item, QListWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:selected, QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: none;
                border-right: 1px solid #dcdcdc;
                border-bottom: 1px solid #dcdcdc;
                font-weight: bold;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1084e3;
            }
            QPushButton:pressed {
                background-color: #006cc1;
            }
            QTextEdit {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                background-color: white;
                padding: 5px;
            }
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #dcdcdc;
            }
            QMenuBar {
                background-color: #f0f0f0;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QSplitter::handle {
                background-color: #e0e0e0;
            }
        """)

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.show()