"""
Model Selection Dialog
Dialog for selecting and configuring segmentation models
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QGroupBox, QFormLayout,
                              QSpinBox, QCheckBox, QTextEdit, QSplitter,
                              QListWidget, QListWidgetItem, QMessageBox, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from models.model_manager import ModelManager, ModelConfig, ModelType, EncoderType
from models.download_manager import DownloadManager
from components.circular_progress import CircularProgress


class ModelListItem(QWidget):
    """Custom list item widget for model selection with download status"""
    
    download_requested = Signal(str)  # model_name
    model_selected = Signal(object)  # config
    
    def __init__(self, config: ModelConfig, download_manager: DownloadManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.download_manager = download_manager
        self.is_selected = False
        
        self.setFixedHeight(70)
        self.setStyleSheet("""
            QWidget {
                background-color: #21252b;
                border: 2px solid #343a40;
                border-radius: 8px;
                margin: 2px;
            }
            QWidget:hover {
                background-color: #343a40;
                border-color: #495057;
            }
        """)
        
        self._setup_ui()
        self._update_download_status()
        
        # Connect to download manager signals
        self.download_manager.progress_updated.connect(self._on_progress_updated)
        self.download_manager.download_completed.connect(self._on_download_completed)
        self.download_manager.download_started.connect(self._on_download_started)
    
    def _setup_ui(self):
        """Setup the UI for the list item"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # Model info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Model name
        self.name_label = QLabel(self.config.model_name)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        info_layout.addWidget(self.name_label)
        
        # Model type and encoder
        self.details_label = QLabel(f"{self.config.model_type.value.upper()} • {self.config.encoder_name.value}")
        self.details_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 11px;
            }
        """)
        info_layout.addWidget(self.details_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Download button/progress
        self.download_widget = QWidget()
        self.download_widget.setFixedSize(50, 50)
        download_layout = QHBoxLayout(self.download_widget)
        download_layout.setContentsMargins(0, 0, 0, 0)
        
        # Download button
        self.download_button = QPushButton("↓")
        self.download_button.setFixedSize(40, 40)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                border-radius: 20px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.download_button.clicked.connect(self._on_download_clicked)
        download_layout.addWidget(self.download_button)
        
        # Progress indicator
        self.progress_indicator = CircularProgress(self.download_widget, 40, 4)
        self.progress_indicator.hide()
        download_layout.addWidget(self.progress_indicator)
        
        layout.addWidget(self.download_widget)
    
    def _update_download_status(self):
        """Update the download status display"""
        progress = self.download_manager.get_download_progress(self.config.model_name)
        
        if progress.is_downloaded:
            self.download_button.setText("✓")
            self.download_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: #ffffff;
                    border: none;
                    border-radius: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
            self.download_button.setEnabled(False)
        elif self.download_manager.is_downloading(self.config.model_name):
            self.download_button.hide()
            self.progress_indicator.show()
        else:
            self.download_button.setText("↓")
            self.download_button.setEnabled(True)
            self.download_button.show()
            self.progress_indicator.hide()
    
    def _on_download_clicked(self):
        """Handle download button click"""
        self.download_requested.emit(self.config.model_name)
    
    def set_selected(self, selected: bool):
        """Set the selection state of this item"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                QWidget {
                    background-color: #495057;
                    border: 2px solid #52a0dc;
                    border-radius: 8px;
                    margin: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #21252b;
                    border: 2px solid #343a40;
                    border-radius: 8px;
                    margin: 2px;
                }
                QWidget:hover {
                    background-color: #343a40;
                    border-color: #495057;
                }
            """)
    
    def mousePressEvent(self, event):
        """Handle mouse press for selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.model_selected.emit(self.config)
        super().mousePressEvent(event)
    
    def _on_download_started(self, model_name: str):
        """Handle download started"""
        if model_name == self.config.model_name:
            self._update_download_status()
    
    def _on_progress_updated(self, model_name: str, progress: float):
        """Handle progress update"""
        if model_name == self.config.model_name:
            self.progress_indicator.set_progress(progress)
    
    def _on_download_completed(self, model_name: str, success: bool, error_message: str):
        """Handle download completion"""
        if model_name == self.config.model_name:
            self._update_download_status()
            if not success:
                # Show error message
                QMessageBox.warning(self, "Download Failed", f"Failed to download {model_name}:\n{error_message}")


class ModelSelectionDialog(QDialog):
    """Dialog for selecting and configuring models"""
    
    model_selected = Signal(ModelConfig)  # Emitted when a model is selected
    
    def __init__(self, model_manager: ModelManager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.selected_config = None
        
        # Initialize download manager
        self.download_manager = DownloadManager()
        self.download_manager.progress_updated.connect(self._on_download_progress)
        self.download_manager.download_completed.connect(self._on_download_completed)
        self.download_manager.download_started.connect(self._on_download_started)
        
        self.setWindowTitle("Load Segmentation Model")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        self._populate_models()
        self._apply_dark_theme()
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Select Segmentation Model")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Model list
        self._create_model_list_panel(splitter)
        
        # Right panel - Configuration
        self._create_config_panel(splitter)
        
        # Set splitter proportions
        splitter.setSizes([300, 500])
        
        # Bottom panel - Model info
        self._create_info_panel(layout)
        
        # Buttons
        self._create_buttons(layout)
    
    def _create_model_list_panel(self, parent):
        """Create the model list panel"""
        panel = QGroupBox("Available Models")
        panel.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #495057;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Model list - using a scroll area with custom widgets instead of QListWidget
        from PySide6.QtWidgets import QScrollArea
        
        self.model_scroll = QScrollArea()
        self.model_scroll.setWidgetResizable(True)
        self.model_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #21252b;
                border: 1px solid #495057;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #343a40;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #495057;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6c757d;
            }
        """)
        
        # Container widget for model items
        self.model_container = QWidget()
        self.model_layout = QVBoxLayout(self.model_container)
        self.model_layout.setContentsMargins(5, 5, 5, 5)
        self.model_layout.setSpacing(5)
        
        self.model_scroll.setWidget(self.model_container)
        layout.addWidget(self.model_scroll)
        
        parent.addWidget(panel)
    
    def _create_config_panel(self, parent):
        """Create the configuration panel"""
        panel = QGroupBox("Model Configuration")
        panel.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #495057;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QFormLayout(panel)
        layout.setSpacing(10)
        
        # Model type
        self.model_type_combo = QComboBox()
        self.model_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #21252b;
                color: #ffffff;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 5px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #21252b;
                color: #ffffff;
                border: 1px solid #495057;
                selection-background-color: #495057;
            }
        """)
        layout.addRow("Model Type:", self.model_type_combo)
        
        # Encoder
        self.encoder_combo = QComboBox()
        self.encoder_combo.setStyleSheet(self.model_type_combo.styleSheet())
        layout.addRow("Encoder:", self.encoder_combo)
        
        # Encoder weights
        self.weights_combo = QComboBox()
        self.weights_combo.setStyleSheet(self.model_type_combo.styleSheet())
        self.weights_combo.addItems(["imagenet", "ssl", "swsl", "instagram", "random"])
        layout.addRow("Weights:", self.weights_combo)
        
        # Input channels
        self.input_channels = QSpinBox()
        self.input_channels.setRange(1, 4)
        self.input_channels.setValue(3)
        self.input_channels.setStyleSheet("""
            QSpinBox {
                background-color: #21252b;
                color: #ffffff;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        layout.addRow("Input Channels:", self.input_channels)
        
        # Output classes
        self.output_classes = QSpinBox()
        self.output_classes.setRange(1, 100)
        self.output_classes.setValue(1)
        self.output_classes.setStyleSheet(self.input_channels.styleSheet())
        layout.addRow("Output Classes:", self.output_classes)
        
        # Activation
        self.activation_combo = QComboBox()
        self.activation_combo.setStyleSheet(self.model_type_combo.styleSheet())
        self.activation_combo.addItems(["None", "sigmoid", "softmax"])
        layout.addRow("Activation:", self.activation_combo)
        
        # Custom name
        self.custom_name = QComboBox()
        self.custom_name.setEditable(True)
        self.custom_name.setStyleSheet(self.model_type_combo.styleSheet())
        layout.addRow("Custom Name:", self.custom_name)
        
        parent.addWidget(panel)
    
    def _create_info_panel(self, parent):
        """Create the model info panel"""
        panel = QGroupBox("Model Information & Use Cases")
        panel.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #495057;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Create tabbed interface for different information sections
        from PySide6.QtWidgets import QTabWidget, QScrollArea, QWidget as QWidgetBase
        
        self.info_tabs = QTabWidget()
        self.info_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #495057;
                background-color: #1a1d23;
                border-radius: 4px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #343a40;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #495057;
            }
            QTabBar::tab:hover {
                background-color: #495057;
            }
        """)
        
        # Description tab (moved to first position)
        self.description_tab = QTextEdit()
        self.description_tab.setReadOnly(True)
        self.description_tab.setStyleSheet("""
            QTextEdit {
                background-color: #1a1d23;
                color: #adb5bd;
                border: none;
                padding: 15px;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        self.info_tabs.addTab(self.description_tab, "Description")
        
        # Image Examples tab (new tab for specific image types)
        self.examples_tab = QTextEdit()
        self.examples_tab.setReadOnly(True)
        self.examples_tab.setStyleSheet(self.description_tab.styleSheet())
        self.info_tabs.addTab(self.examples_tab, "Image Examples")
        
        # Use Cases tab
        self.usecases_tab = QTextEdit()
        self.usecases_tab.setReadOnly(True)
        self.usecases_tab.setStyleSheet(self.description_tab.styleSheet())
        self.info_tabs.addTab(self.usecases_tab, "Use Cases")
        
        # Pros & Cons tab
        self.proscons_tab = QTextEdit()
        self.proscons_tab.setReadOnly(True)
        self.proscons_tab.setStyleSheet(self.description_tab.styleSheet())
        self.info_tabs.addTab(self.proscons_tab, "Pros & Cons")
        
        # Best For tab
        self.bestfor_tab = QTextEdit()
        self.bestfor_tab.setReadOnly(True)
        self.bestfor_tab.setStyleSheet(self.description_tab.styleSheet())
        self.info_tabs.addTab(self.bestfor_tab, "Best For")
        
        # Set initial content
        self._update_info_tabs("Select a model to see detailed information...")
        
        layout.addWidget(self.info_tabs)
        parent.addWidget(panel)
        
    
    def _create_buttons(self, parent):
        """Create the dialog buttons"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Load button
        self.load_button = QPushButton("Load Model")
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.load_button.clicked.connect(self._load_model)
        self.load_button.setEnabled(False)
        button_layout.addWidget(self.load_button)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        parent.addLayout(button_layout)
    
    def _populate_models(self):
        """Populate the model list with available models"""
        available_models = self.model_manager.get_available_models()
        self.model_items = {}  # Store model items for selection management
        
        for name, config in available_models.items():
            # Create custom list item widget
            list_item_widget = ModelListItem(config, self.download_manager)
            list_item_widget.download_requested.connect(self._on_download_requested)
            list_item_widget.model_selected.connect(self._on_model_selected)
            
            # Add to layout
            self.model_layout.addWidget(list_item_widget)
            self.model_items[name] = list_item_widget
        
        # Add stretch to push items to top
        self.model_layout.addStretch()
        
        # Auto-select first model to show information immediately
        if self.model_items:
            first_model_name = list(self.model_items.keys())[0]
            first_item = self.model_items[first_model_name]
            self._on_model_selected(first_item.config)
        
        # Populate combo boxes
        for model_type in ModelType:
            self.model_type_combo.addItem(model_type.value.upper(), model_type)
        
        for encoder in EncoderType:
            self.encoder_combo.addItem(encoder.value, encoder)
    
    def _on_model_selected(self, config: ModelConfig):
        """Handle model selection from list"""
        # Deselect all other items
        for name, item in self.model_items.items():
            item.set_selected(name == config.model_name)
        
        # Update configuration and info
        self._update_config_from_selection(config)
        self._update_model_info(config)
        self.load_button.setEnabled(True)
    
    def _update_config_from_selection(self, config: ModelConfig):
        """Update configuration controls from selected model"""
        # Find and select model type
        for i in range(self.model_type_combo.count()):
            if self.model_type_combo.itemData(i) == config.model_type:
                self.model_type_combo.setCurrentIndex(i)
                break
        
        # Find and select encoder
        for i in range(self.encoder_combo.count()):
            if self.encoder_combo.itemData(i) == config.encoder_name:
                self.encoder_combo.setCurrentIndex(i)
                break
        
        # Set other values
        self.weights_combo.setCurrentText(config.encoder_weights)
        self.input_channels.setValue(config.in_channels)
        self.output_classes.setValue(config.classes)
        self.activation_combo.setCurrentText(config.activation or "None")
        self.custom_name.setCurrentText(config.model_name)
    
    def _update_model_info(self, config: ModelConfig):
        """Update the model information display"""
        try:
            # Get detailed description from model manager
            description = self.model_manager.get_model_description(config.model_name)
            
            # Update Description tab (now first tab with description at top)
            description_text = f"""{description['description']}

Model Configuration:
• Model: {config.model_name}
• Type: {config.model_type.value.upper()}
• Encoder: {config.encoder_name.value}
• Weights: {config.encoder_weights}
• Input Channels: {config.in_channels}
• Output Classes: {config.classes}
• Activation: {config.activation or 'None'}"""
            
            self.description_tab.setPlainText(description_text)
            
            # Update Image Examples tab (new tab with specific image types)
            self.examples_tab.setPlainText(description.get('image_examples', 'No image examples available'))
            
            # Update Use Cases tab
            self.usecases_tab.setPlainText(description.get('use_cases', 'No use cases available'))
            
            # Update Pros & Cons tab
            pros_cons_text = f"""Advantages:
{description.get('pros', 'No advantages listed')}

Disadvantages:
{description.get('cons', 'No disadvantages listed')}"""
            self.proscons_tab.setPlainText(pros_cons_text)
            
            # Update Best For tab
            self.bestfor_tab.setPlainText(description.get('best_for', 'No recommendations available'))
            
        except Exception as e:
            # Fallback if there's an error
            error_text = f"Error loading model information: {str(e)}"
            self.description_tab.setPlainText(error_text)
            self.examples_tab.setPlainText(error_text)
            self.usecases_tab.setPlainText(error_text)
            self.proscons_tab.setPlainText(error_text)
            self.bestfor_tab.setPlainText(error_text)
    
    def _update_info_tabs(self, message: str):
        """Update all info tabs with a message"""
        self.description_tab.setPlainText(message)
        self.examples_tab.setPlainText(message)
        self.usecases_tab.setPlainText(message)
        self.proscons_tab.setPlainText(message)
        self.bestfor_tab.setPlainText(message)
    
    def _load_model(self):
        """Load the configured model"""
        try:
            # Create configuration from current settings
            model_type = self.model_type_combo.currentData()
            encoder = self.encoder_combo.currentData()
            weights = self.weights_combo.currentText()
            in_channels = self.input_channels.value()
            classes = self.output_classes.value()
            activation = self.activation_combo.currentText()
            if activation == "None":
                activation = None
            
            custom_name = self.custom_name.currentText()
            if not custom_name:
                custom_name = f"{model_type.value}_{encoder.value}"
            
            config = ModelConfig(
                model_type=model_type,
                encoder_name=encoder,
                encoder_weights=weights,
                in_channels=in_channels,
                classes=classes,
                activation=activation,
                model_name=custom_name
            )
            
            # Emit signal with configuration
            self.model_selected.emit(config)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create model configuration:\n{str(e)}")
    
    def _apply_dark_theme(self):
        """Apply dark theme to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2c313a;
            }
        """)
    
    def _on_download_requested(self, model_name: str):
        """Handle download request from list item"""
        available_models = self.model_manager.get_available_models()
        if model_name in available_models:
            config = available_models[model_name]
            self.download_manager.start_download(config)
    
    def _on_download_started(self, model_name: str):
        """Handle download started"""
        print(f"Download started: {model_name}")
    
    def _on_download_progress(self, model_name: str, progress: float):
        """Handle download progress update"""
        print(f"Download progress {model_name}: {progress}%")
    
    def _on_download_completed(self, model_name: str, success: bool, error_message: str):
        """Handle download completion"""
        if success:
            print(f"Download completed: {model_name}")
        else:
            print(f"Download failed: {model_name} - {error_message}")
