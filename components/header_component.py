"""
Header Component
Contains the application header with menu and status indicators
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                            QPushButton, QMenuBar, QMenu, QStatusBar, QFrame)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush
from models.application_state import StatusType, StatusLevel


class StatusPill(QWidget):
    """Green pill status indicator widget"""
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.label = label
        self.status_level = StatusLevel.UNKNOWN
        self.message = "Unknown"
        self.details = ""
        
        self.setFixedSize(120, 30)
        self.setToolTip(f"{self.label}: {self.message}")
    
    def set_status(self, level: StatusLevel, message: str, details: str = ""):
        """Update the status of the pill"""
        self.status_level = level
        self.message = message
        self.details = details
        self.setToolTip(f"{self.label}: {self.message}\n{self.details}")
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for the pill"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get colors based on status level
        if self.status_level == StatusLevel.SUCCESS:
            bg_color = QColor(40, 167, 69)    # Green
            text_color = QColor(255, 255, 255)  # White
        elif self.status_level == StatusLevel.WARNING:
            bg_color = QColor(255, 193, 7)    # Yellow
            text_color = QColor(0, 0, 0)      # Black
        elif self.status_level == StatusLevel.ERROR:
            bg_color = QColor(220, 53, 69)    # Red
            text_color = QColor(255, 255, 255)  # White
        else:  # UNKNOWN
            bg_color = QColor(108, 117, 125)  # Gray
            text_color = QColor(255, 255, 255)  # White
        
        # Draw pill background
        rect = self.rect()
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 15, 15)
        
        # Draw text
        painter.setPen(QPen(text_color))
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.label)


class HeaderComponent(QWidget):
    """Header component with menu and status indicators"""
    
    # Signals
    menu_action_triggered = Signal(str)  # action_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QWidget {
                background-color: #21252b;
                border-bottom: 1px solid #495057;
            }
            QMenuBar {
                background-color: #21252b;
                color: #ffffff;
                border: none;
                padding: 5px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #495057;
            }
            QMenu {
                background-color: #2c313a;
                color: #ffffff;
                border: 1px solid #495057;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #495057;
            }
        """)
        
        self._setup_ui()
        self._setup_status_indicators()
    
    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top row: Menu bar
        menu_layout = QHBoxLayout()
        menu_layout.setContentsMargins(20, 10, 20, 5)
        
        # Application title
        title_label = QLabel("ImageEmboss")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        menu_layout.addWidget(title_label)
        
        # Menu bar
        self.menu_bar = QMenuBar()
        self._create_menus()
        menu_layout.addWidget(self.menu_bar)
        
        # Status indicators (right side)
        self.status_layout = QHBoxLayout()
        self.status_layout.setSpacing(10)
        menu_layout.addLayout(self.status_layout)
        
        layout.addLayout(menu_layout)
        
        # Bottom row: Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #2c313a;
                color: #adb5bd;
                border-top: 1px solid #495057;
                padding: 5px 20px;
            }
        """)
        self.status_bar.showMessage("Ready")
        layout.addWidget(self.status_bar)
    
    def _create_menus(self):
        """Create application menus"""
        # File menu
        file_menu = self.menu_bar.addMenu("File")
        
        new_action = file_menu.addAction("New Project")
        new_action.triggered.connect(lambda: self.menu_action_triggered.emit("new_project"))
        
        open_action = file_menu.addAction("Open Image")
        open_action.triggered.connect(lambda: self.menu_action_triggered.emit("open_image"))
        
        file_menu.addSeparator()
        
        save_action = file_menu.addAction("Save")
        save_action.triggered.connect(lambda: self.menu_action_triggered.emit("save"))
        
        save_as_action = file_menu.addAction("Save As...")
        save_as_action.triggered.connect(lambda: self.menu_action_triggered.emit("save_as"))
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(lambda: self.menu_action_triggered.emit("exit"))
        
        # Edit menu
        edit_menu = self.menu_bar.addMenu("Edit")
        
        undo_action = edit_menu.addAction("Undo")
        undo_action.triggered.connect(lambda: self.menu_action_triggered.emit("undo"))
        
        redo_action = edit_menu.addAction("Redo")
        redo_action.triggered.connect(lambda: self.menu_action_triggered.emit("redo"))
        
        # View menu
        view_menu = self.menu_bar.addMenu("View")
        
        fullscreen_action = view_menu.addAction("Toggle Fullscreen")
        fullscreen_action.triggered.connect(lambda: self.menu_action_triggered.emit("toggle_fullscreen"))
        
        # Tools menu
        tools_menu = self.menu_bar.addMenu("Tools")
        
        load_model_action = tools_menu.addAction("Load Model")
        load_model_action.triggered.connect(lambda: self.menu_action_triggered.emit("load_model"))
        
        settings_action = tools_menu.addAction("Settings")
        settings_action.triggered.connect(lambda: self.menu_action_triggered.emit("settings"))
        
        # Help menu
        help_menu = self.menu_bar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(lambda: self.menu_action_triggered.emit("about"))
    
    def _setup_status_indicators(self):
        """Setup status indicator pills"""
        # GPU Status
        self.gpu_pill = StatusPill("GPU")
        self.status_layout.addWidget(self.gpu_pill)
        
        # CUDA Status
        self.cuda_pill = StatusPill("CUDA")
        self.status_layout.addWidget(self.cuda_pill)
        
        # ML Model Status
        self.model_pill = StatusPill("MODEL")
        self.status_layout.addWidget(self.model_pill)
        
        # System Status
        self.system_pill = StatusPill("SYSTEM")
        self.status_layout.addWidget(self.system_pill)
    
    def update_status(self, status_type: StatusType, level: StatusLevel, message: str, details: str = ""):
        """Update a status indicator"""
        if status_type == StatusType.GPU:
            self.gpu_pill.set_status(level, message, details)
        elif status_type == StatusType.CUDA:
            self.cuda_pill.set_status(level, message, details)
        elif status_type == StatusType.ML_MODEL:
            self.model_pill.set_status(level, message, details)
        elif status_type == StatusType.SYSTEM:
            self.system_pill.set_status(level, message, details)
    
    def set_status_message(self, message: str):
        """Set the status bar message"""
        self.status_bar.showMessage(message)
