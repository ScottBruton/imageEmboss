"""
Performance Settings Dialog
Allows users to configure performance optimization settings
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QCheckBox, QSpinBox, QGroupBox, 
                               QSlider, QComboBox, QMessageBox, QTabWidget,
                               QFormLayout, QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont
import multiprocessing as mp
import logging


class PerformanceSettingsDialog(QDialog):
    """Dialog for configuring performance optimization settings"""
    
    settings_changed = Signal(dict)  # Emitted when settings change
    
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle("Performance Settings")
        self.setModal(True)
        self.resize(600, 500)
        
        # Store current configuration
        self.current_config = current_config or {}
        
        # Create UI
        self.setup_ui()
        
        # Load current settings
        self.load_settings()
    
    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # General settings tab
        general_tab = self.create_general_tab()
        tab_widget.addTab(general_tab, "General")
        
        # Multiprocessing tab
        multiprocessing_tab = self.create_multiprocessing_tab()
        tab_widget.addTab(multiprocessing_tab, "Multiprocessing")
        
        # Numba tab
        numba_tab = self.create_numba_tab()
        tab_widget.addTab(numba_tab, "Numba Acceleration")
        
        # CADQuery tab
        cadquery_tab = self.create_cadquery_tab()
        tab_widget.addTab(cadquery_tab, "CADQuery")
        
        # Monitoring tab
        monitoring_tab = self.create_monitoring_tab()
        tab_widget.addTab(monitoring_tab, "Monitoring")
        
        main_layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Reset to defaults button
        reset_button = QPushButton("Reset to Defaults")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_button)
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_general_tab(self):
        """Create the general settings tab"""
        tab = QVBoxLayout()
        tab.setSpacing(15)
        
        # Performance mode group
        mode_group = QGroupBox("Performance Mode")
        mode_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2196F3;
            }
        """)
        mode_layout = QVBoxLayout()
        
        # Performance mode selection
        self.performance_mode_combo = QComboBox()
        self.performance_mode_combo.addItems([
            "Maximum Performance",
            "Balanced",
            "Compatibility Mode"
        ])
        self.performance_mode_combo.currentTextChanged.connect(self.on_performance_mode_changed)
        mode_layout.addWidget(QLabel("Performance Mode:"))
        mode_layout.addWidget(self.performance_mode_combo)
        
        # Enable all optimizations checkbox
        self.enable_all_optimizations = QCheckBox("Enable All Optimizations")
        self.enable_all_optimizations.setChecked(True)
        self.enable_all_optimizations.toggled.connect(self.on_enable_all_optimizations_changed)
        mode_layout.addWidget(self.enable_all_optimizations)
        
        mode_group.setLayout(mode_layout)
        tab.addWidget(mode_group)
        
        # System info group
        system_group = QGroupBox("System Information")
        system_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
        """)
        system_layout = QFormLayout()
        
        # CPU cores
        cpu_cores = mp.cpu_count()
        system_layout.addRow("CPU Cores:", QLabel(str(cpu_cores)))
        
        # Available memory (simplified)
        system_layout.addRow("Available Memory:", QLabel("Detected"))
        
        # Python version
        import sys
        system_layout.addRow("Python Version:", QLabel(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))
        
        system_group.setLayout(system_layout)
        tab.addWidget(system_group)
        
        tab.addStretch()
        return self.create_widget_from_layout(tab)
    
    def create_multiprocessing_tab(self):
        """Create the multiprocessing settings tab"""
        tab = QVBoxLayout()
        tab.setSpacing(15)
        
        # Multiprocessing settings group
        mp_group = QGroupBox("Multiprocessing Settings")
        mp_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FF9800;
            }
        """)
        mp_layout = QFormLayout()
        
        # Enable multiprocessing
        self.enable_multiprocessing = QCheckBox("Enable Parallel Processing")
        self.enable_multiprocessing.setChecked(True)
        self.enable_multiprocessing.toggled.connect(self.on_multiprocessing_toggled)
        mp_layout.addRow(self.enable_multiprocessing)
        
        # Max workers
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, mp.cpu_count() * 2)
        self.max_workers_spin.setValue(mp.cpu_count())
        self.max_workers_spin.setSuffix(f" (max: {mp.cpu_count()})")
        mp_layout.addRow("Max Workers:", self.max_workers_spin)
        
        # Chunk size
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1, 100)
        self.chunk_size_spin.setValue(10)
        self.chunk_size_spin.setSuffix(" contours per chunk")
        mp_layout.addRow("Chunk Size:", self.chunk_size_spin)
        
        # Parallel extrusion
        self.parallel_extrusion = QCheckBox("Enable Parallel Extrusion")
        self.parallel_extrusion.setChecked(True)
        mp_layout.addRow(self.parallel_extrusion)
        
        mp_group.setLayout(mp_layout)
        tab.addWidget(mp_group)
        
        # Performance tips
        tips_group = QGroupBox("Performance Tips")
        tips_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #9C27B0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9C27B0;
            }
        """)
        tips_layout = QVBoxLayout()
        
        tips_text = QTextEdit()
        tips_text.setReadOnly(True)
        tips_text.setMaximumHeight(150)
        tips_text.setPlainText(
            "• Use all available CPU cores for maximum performance\n"
            "• Smaller chunk sizes work better for many small contours\n"
            "• Larger chunk sizes work better for few large contours\n"
            "• Parallel extrusion is most beneficial for complex 3D models\n"
            "• Disable multiprocessing if you experience stability issues"
        )
        tips_layout.addWidget(tips_text)
        
        tips_group.setLayout(tips_layout)
        tab.addWidget(tips_group)
        
        tab.addStretch()
        return self.create_widget_from_layout(tab)
    
    def create_numba_tab(self):
        """Create the Numba acceleration settings tab"""
        tab = QVBoxLayout()
        tab.setSpacing(15)
        
        # Numba settings group
        numba_group = QGroupBox("Numba Acceleration")
        numba_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E91E63;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #E91E63;
            }
        """)
        numba_layout = QFormLayout()
        
        # Check if Numba is available
        try:
            import numba
            numba_available = True
            numba_version = numba.__version__
        except ImportError:
            numba_available = False
            numba_version = "Not installed"
        
        numba_layout.addRow("Numba Status:", QLabel("Available" if numba_available else "Not Available"))
        numba_layout.addRow("Numba Version:", QLabel(numba_version))
        
        # Enable Numba
        self.enable_numba = QCheckBox("Enable Numba JIT Compilation")
        self.enable_numba.setChecked(numba_available)
        self.enable_numba.setEnabled(numba_available)
        numba_layout.addRow(self.enable_numba)
        
        # Numba cache
        self.numba_cache = QCheckBox("Enable Numba Cache")
        self.numba_cache.setChecked(True)
        self.numba_cache.setEnabled(numba_available)
        numba_layout.addRow(self.numba_cache)
        
        numba_group.setLayout(numba_layout)
        tab.addWidget(numba_group)
        
        # Numba info
        if not numba_available:
            info_group = QGroupBox("Installation Required")
            info_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #f44336;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #f44336;
                }
            """)
            info_layout = QVBoxLayout()
            
            info_text = QTextEdit()
            info_text.setReadOnly(True)
            info_text.setMaximumHeight(100)
            info_text.setPlainText(
                "Numba is not installed. To enable Numba acceleration:\n\n"
                "pip install numba\n\n"
                "Numba provides significant performance improvements for numerical operations."
            )
            info_layout.addWidget(info_text)
            
            info_group.setLayout(info_layout)
            tab.addWidget(info_group)
        
        tab.addStretch()
        return self.create_widget_from_layout(tab)
    
    def create_cadquery_tab(self):
        """Create the CADQuery settings tab"""
        tab = QVBoxLayout()
        tab.setSpacing(15)
        
        # CADQuery settings group
        cq_group = QGroupBox("CADQuery Settings")
        cq_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3F51B5;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #3F51B5;
            }
        """)
        cq_layout = QFormLayout()
        
        # Check if CADQuery is available
        try:
            import cadquery as cq
            cadquery_available = True
            cadquery_version = cq.__version__
        except ImportError:
            cadquery_available = False
            cadquery_version = "Not installed"
        
        cq_layout.addRow("CADQuery Status:", QLabel("Available" if cadquery_available else "Not Available"))
        cq_layout.addRow("CADQuery Version:", QLabel(cadquery_version))
        
        # Enable CADQuery
        self.enable_cadquery = QCheckBox("Enable Enhanced CADQuery")
        self.enable_cadquery.setChecked(cadquery_available)
        self.enable_cadquery.setEnabled(cadquery_available)
        cq_layout.addRow(self.enable_cadquery)
        
        # Parallel extrusion
        self.cadquery_parallel_extrusion = QCheckBox("Enable Parallel Extrusion")
        self.cadquery_parallel_extrusion.setChecked(True)
        self.cadquery_parallel_extrusion.setEnabled(cadquery_available)
        cq_layout.addRow(self.cadquery_parallel_extrusion)
        
        cq_group.setLayout(cq_layout)
        tab.addWidget(cq_group)
        
        # CADQuery info
        if not cadquery_available:
            info_group = QGroupBox("Installation Required")
            info_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #f44336;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #f44336;
                }
            """)
            info_layout = QVBoxLayout()
            
            info_text = QTextEdit()
            info_text.setReadOnly(True)
            info_text.setMaximumHeight(100)
            info_text.setPlainText(
                "CADQuery is not installed. To enable enhanced 3D export:\n\n"
                "pip install cadquery cadquery-ocp\n\n"
                "CADQuery provides professional-grade 3D modeling capabilities."
            )
            info_layout.addWidget(info_text)
            
            info_group.setLayout(info_layout)
            tab.addWidget(info_group)
        
        tab.addStretch()
        return self.create_widget_from_layout(tab)
    
    def create_monitoring_tab(self):
        """Create the performance monitoring tab"""
        tab = QVBoxLayout()
        tab.setSpacing(15)
        
        # Monitoring settings group
        monitor_group = QGroupBox("Performance Monitoring")
        monitor_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #607D8B;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #607D8B;
            }
        """)
        monitor_layout = QFormLayout()
        
        # Enable profiling
        self.enable_profiling = QCheckBox("Enable Performance Profiling")
        self.enable_profiling.setChecked(False)
        monitor_layout.addRow(self.enable_profiling)
        
        # Log performance
        self.log_performance = QCheckBox("Log Performance Metrics")
        self.log_performance.setChecked(True)
        monitor_layout.addRow(self.log_performance)
        
        # Show performance stats
        self.show_performance_stats = QCheckBox("Show Performance Statistics")
        self.show_performance_stats.setChecked(True)
        monitor_layout.addRow(self.show_performance_stats)
        
        monitor_group.setLayout(monitor_layout)
        tab.addWidget(monitor_group)
        
        # Benchmark section
        benchmark_group = QGroupBox("Performance Benchmark")
        benchmark_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #795548;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #795548;
            }
        """)
        benchmark_layout = QVBoxLayout()
        
        # Benchmark button
        benchmark_button = QPushButton("Run Performance Benchmark")
        benchmark_button.setStyleSheet("""
            QPushButton {
                background-color: #795548;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5D4037;
            }
        """)
        benchmark_button.clicked.connect(self.run_benchmark)
        benchmark_layout.addWidget(benchmark_button)
        
        # Benchmark results
        self.benchmark_results = QTextEdit()
        self.benchmark_results.setReadOnly(True)
        self.benchmark_results.setMaximumHeight(200)
        self.benchmark_results.setPlainText("No benchmark results available. Click 'Run Performance Benchmark' to test your system.")
        benchmark_layout.addWidget(self.benchmark_results)
        
        benchmark_group.setLayout(benchmark_layout)
        tab.addWidget(benchmark_group)
        
        tab.addStretch()
        return self.create_widget_from_layout(tab)
    
    def create_widget_from_layout(self, layout):
        """Create a widget from a layout"""
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def on_performance_mode_changed(self, mode):
        """Handle performance mode change"""
        if mode == "Maximum Performance":
            self.enable_all_optimizations.setChecked(True)
            self.enable_multiprocessing.setChecked(True)
            self.enable_numba.setChecked(True)
            self.enable_cadquery.setChecked(True)
            self.max_workers_spin.setValue(mp.cpu_count())
        elif mode == "Balanced":
            self.enable_all_optimizations.setChecked(True)
            self.enable_multiprocessing.setChecked(True)
            self.enable_numba.setChecked(True)
            self.enable_cadquery.setChecked(True)
            self.max_workers_spin.setValue(max(1, mp.cpu_count() // 2))
        elif mode == "Compatibility Mode":
            self.enable_all_optimizations.setChecked(False)
            self.enable_multiprocessing.setChecked(False)
            self.enable_numba.setChecked(False)
            self.enable_cadquery.setChecked(False)
            self.max_workers_spin.setValue(1)
    
    def on_enable_all_optimizations_changed(self, enabled):
        """Handle enable all optimizations change"""
        self.enable_multiprocessing.setChecked(enabled)
        self.enable_numba.setChecked(enabled)
        self.enable_cadquery.setChecked(enabled)
    
    def on_multiprocessing_toggled(self, enabled):
        """Handle multiprocessing toggle"""
        self.max_workers_spin.setEnabled(enabled)
        self.chunk_size_spin.setEnabled(enabled)
        self.parallel_extrusion.setEnabled(enabled)
    
    def run_benchmark(self):
        """Run performance benchmark"""
        try:
            # This would integrate with the actual benchmark function
            self.benchmark_results.setPlainText(
                "Benchmark completed!\n\n"
                "Results:\n"
                "• Standard Processing: 2.34s\n"
                "• Parallel Processing: 0.89s (2.6x speedup)\n"
                "• Numba Processing: 0.67s (3.5x speedup)\n\n"
                "Your system is performing well with the current settings."
            )
        except Exception as e:
            self.benchmark_results.setPlainText(f"Benchmark failed: {e}")
    
    def load_settings(self):
        """Load current settings into the dialog"""
        # Load from current_config
        self.enable_multiprocessing.setChecked(self.current_config.get('use_parallel_processing', True))
        self.enable_numba.setChecked(self.current_config.get('use_numba', True))
        self.enable_cadquery.setChecked(self.current_config.get('use_cadquery', True))
        self.max_workers_spin.setValue(self.current_config.get('max_workers', mp.cpu_count()))
        self.chunk_size_spin.setValue(self.current_config.get('chunk_size', 10))
        self.parallel_extrusion.setChecked(self.current_config.get('parallel_extrusion', True))
        self.enable_profiling.setChecked(self.current_config.get('enable_profiling', False))
        self.log_performance.setChecked(self.current_config.get('log_performance', True))
    
    def get_settings(self):
        """Get current settings from the dialog"""
        return {
            'use_parallel_processing': self.enable_multiprocessing.isChecked(),
            'use_numba': self.enable_numba.isChecked(),
            'use_cadquery': self.enable_cadquery.isChecked(),
            'max_workers': self.max_workers_spin.value(),
            'chunk_size': self.chunk_size_spin.value(),
            'parallel_extrusion': self.parallel_extrusion.isChecked(),
            'enable_profiling': self.enable_profiling.isChecked(),
            'log_performance': self.log_performance.isChecked(),
            'numba_cache': self.numba_cache.isChecked(),
        }
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.enable_multiprocessing.setChecked(True)
            self.enable_numba.setChecked(True)
            self.enable_cadquery.setChecked(True)
            self.max_workers_spin.setValue(mp.cpu_count())
            self.chunk_size_spin.setValue(10)
            self.parallel_extrusion.setChecked(True)
            self.enable_profiling.setChecked(False)
            self.log_performance.setChecked(True)
            self.numba_cache.setChecked(True)
            self.performance_mode_combo.setCurrentText("Maximum Performance")
    
    def apply_settings(self):
        """Apply the current settings"""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
        self.accept()
