"""
Custom UI controls for ImageEmboss
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSlider, QSpinBox, QDoubleSpinBox, QCheckBox, 
                               QComboBox, QPushButton, QGroupBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Any, Callable


class ParameterSlider(QWidget):
    """Custom slider with label and value display"""
    
    value_changed = Signal(float)
    
    def __init__(self, label: str, min_val: float, max_val: float, 
                 default_val: float, step: float = 1.0, decimals: int = 0, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.min_val = min_val
        self.max_val = max_val
        self.default_val = default_val
        self.step = step
        self.decimals = decimals
        
        self.setup_ui()
        self.set_value(default_val)
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        self.label = QLabel(self.label_text)
        self.label.setFont(QFont("Arial", 9))
        layout.addWidget(self.label)
        
        # Slider and value
        slider_layout = QHBoxLayout()
        
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self.slider)
        
        # Value display
        if self.decimals > 0:
            self.value_spinbox = QDoubleSpinBox()
            self.value_spinbox.setDecimals(self.decimals)
        else:
            self.value_spinbox = QSpinBox()
        
        self.value_spinbox.setMinimum(self.min_val)
        self.value_spinbox.setMaximum(self.max_val)
        self.value_spinbox.setSingleStep(self.step)
        self.value_spinbox.valueChanged.connect(self._on_spinbox_changed)
        self.value_spinbox.setFixedWidth(80)
        slider_layout.addWidget(self.value_spinbox)
        
        layout.addLayout(slider_layout)
    
    def _on_slider_changed(self, value: int):
        """Handle slider value change"""
        # Convert slider value (0-1000) to actual value
        actual_value = self.min_val + (value / 1000.0) * (self.max_val - self.min_val)
        actual_value = round(actual_value / self.step) * self.step
        actual_value = max(self.min_val, min(self.max_val, actual_value))
        
        # Update spinbox without triggering signal
        self.value_spinbox.blockSignals(True)
        self.value_spinbox.setValue(actual_value)
        self.value_spinbox.blockSignals(False)
        
        # Emit signal
        self.value_changed.emit(actual_value)
    
    def _on_spinbox_changed(self, value: float):
        """Handle spinbox value change"""
        # Update slider without triggering signal
        self.slider.blockSignals(True)
        slider_value = int((value - self.min_val) / (self.max_val - self.min_val) * 1000)
        self.slider.setValue(slider_value)
        self.slider.blockSignals(False)
        
        # Emit signal
        self.value_changed.emit(value)
    
    def get_value(self) -> float:
        """Get current value"""
        return self.value_spinbox.value()
    
    def set_value(self, value: float):
        """Set value"""
        value = max(self.min_val, min(self.max_val, value))
        self.value_spinbox.setValue(value)
    
    def set_enabled(self, enabled: bool):
        """Enable/disable control"""
        self.slider.setEnabled(enabled)
        self.value_spinbox.setEnabled(enabled)


class PresetComboBox(QComboBox):
    """Custom combo box for presets"""
    
    preset_changed = Signal(str)
    
    def __init__(self, presets: dict, parent=None):
        super().__init__(parent)
        self.presets = presets
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI components"""
        self.addItems(list(self.presets.keys()))
        self.currentTextChanged.connect(self.preset_changed.emit)
    
    def get_current_preset(self) -> str:
        """Get current preset name"""
        return self.currentText()
    
    def set_preset(self, preset_name: str):
        """Set preset by name"""
        if preset_name in self.presets:
            self.setCurrentText(preset_name)


class ProcessingButton(QPushButton):
    """Custom button for processing actions"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI components"""
        self.setMinimumHeight(40)
        self.setFont(QFont("Arial", 10, QFont.Bold))
        self.setStyleSheet("""
            QPushButton {
                background-color: #2E86AB;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1E6B8B;
            }
            QPushButton:pressed {
                background-color: #0E4B6B;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)


class StatusLabel(QLabel):
    """Custom label for status display"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI components"""
        self.setFont(QFont("Arial", 9))
        self.setStyleSheet("""
            QLabel {
                color: #666666;
                background-color: #F5F5F5;
                border: 1px solid #DDDDDD;
                border-radius: 3px;
                padding: 4px 8px;
            }
        """)
    
    def set_status(self, status: str, color: str = "#666666"):
        """Set status text and color"""
        self.setText(status)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: #F5F5F5;
                border: 1px solid #DDDDDD;
                border-radius: 3px;
                padding: 4px 8px;
            }}
        """)


class ProgressBar(QWidget):
    """Custom progress bar"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #DDDDDD;
                border-radius: 3px;
                text-align: center;
                background-color: #F5F5F5;
            }
            QProgressBar::chunk {
                background-color: #2E86AB;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 8))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def set_progress(self, value: int, status: str = ""):
        """Set progress value and status"""
        self.progress_bar.setValue(value)
        if status:
            self.status_label.setText(status)
    
    def reset(self):
        """Reset progress bar"""
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")


class ToolButton(QPushButton):
    """Custom tool button"""
    
    def __init__(self, text: str, tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setup_ui()
        if tooltip:
            self.setToolTip(tooltip)
    
    def setup_ui(self):
        """Setup UI components"""
        self.setMinimumHeight(30)
        self.setFont(QFont("Arial", 9))
        self.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #DDDDDD;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
                border-color: #2E86AB;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
            QPushButton:checked {
                background-color: #2E86AB;
                color: white;
            }
        """)
    
    def set_active(self, active: bool):
        """Set active state"""
        self.setChecked(active)


# Import QProgressBar
try:
    from PySide6.QtWidgets import QProgressBar
except ImportError:
    print("⚠️ QProgressBar not available - progress display will be limited")
    QProgressBar = None
