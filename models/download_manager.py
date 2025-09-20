"""
Download Manager
Handles background downloading of model weights with progress tracking
"""

import os
import sys
import torch
import segmentation_models_pytorch as smp
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread, QMutex, QMutexLocker
from typing import Dict, Optional
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.model_manager import ModelConfig, ModelType, EncoderType


class DownloadProgress:
    """Represents download progress for a model"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.status = "pending"  # pending, downloading, completed, failed
        self.progress = 0.0  # 0.0 to 100.0
        self.error_message = ""
        self.start_time = None
        self.end_time = None
    
    def start_download(self):
        """Mark download as started"""
        self.status = "downloading"
        self.progress = 0.0
        self.start_time = time.time()
        self.error_message = ""
    
    def update_progress(self, progress: float):
        """Update download progress"""
        self.progress = min(100.0, max(0.0, progress))
    
    def complete_download(self):
        """Mark download as completed"""
        self.status = "completed"
        self.progress = 100.0
        self.end_time = time.time()
    
    def fail_download(self, error_message: str):
        """Mark download as failed"""
        self.status = "failed"
        self.error_message = error_message
        self.end_time = time.time()
    
    @property
    def is_downloaded(self) -> bool:
        """Check if model weights are already downloaded"""
        return self._check_weights_cached()
    
    def _check_weights_cached(self) -> bool:
        """Check if weights are cached for this model"""
        try:
            # This is a simplified check - in practice, you'd check for specific weight files
            torch_cache = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
            if not torch_cache.exists():
                return False
            
            # Check for common weight files that would be downloaded
            cached_files = list(torch_cache.glob("*.pth"))
            return len(cached_files) > 0
        except:
            return False


class DownloadWorker(QThread):
    """Worker thread for downloading model weights"""
    
    progress_updated = Signal(str, float)  # model_name, progress
    download_completed = Signal(str, bool, str)  # model_name, success, error_message
    download_started = Signal(str)  # model_name
    
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        self.should_stop = False
        self.mutex = QMutex()
    
    def run(self):
        """Download model weights in background"""
        model_name = self.config.model_name
        
        try:
            self.download_started.emit(model_name)
            
            # Simulate progress updates
            for progress in [10, 25, 50, 75, 90, 100]:
                if self.should_stop:
                    return
                
                self.progress_updated.emit(model_name, progress)
                self.msleep(200)  # Simulate download time
            
            # Actually create the model to trigger weight download
            self._download_model_weights()
            
            self.download_completed.emit(model_name, True, "")
            
        except Exception as e:
            self.download_completed.emit(model_name, False, str(e))
    
    def _download_model_weights(self):
        """Download weights for the specific model"""
        model_type = self.config.model_type.value
        encoder_name = self.config.encoder_name.value
        
        if model_type == "unet":
            model = smp.Unet(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        elif model_type == "fpn":
            model = smp.FPN(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        elif model_type == "pspnet":
            model = smp.PSPNet(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        elif model_type == "linknet":
            model = smp.Linknet(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        elif model_type == "pan":
            model = smp.PAN(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        elif model_type == "manet":
            model = smp.MAnet(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        elif model_type == "deeplabv3":
            model = smp.DeepLabV3(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        elif model_type == "deeplabv3plus":
            model = smp.DeepLabV3Plus(
                encoder_name=encoder_name,
                encoder_weights=self.config.encoder_weights,
                in_channels=self.config.in_channels,
                classes=self.config.classes,
                activation=self.config.activation,
            )
        
        # Test the model to ensure weights are properly loaded
        input_size = 512 if model_type in ["pspnet", "deeplabv3plus", "pan"] else 224
        dummy_input = torch.randn(1, self.config.in_channels, input_size, input_size)
        with torch.no_grad():
            _ = model(dummy_input)
    
    def stop(self):
        """Stop the download"""
        with QMutexLocker(self.mutex):
            self.should_stop = True


class DownloadManager(QObject):
    """Manages background downloads of model weights"""
    
    progress_updated = Signal(str, float)  # model_name, progress
    download_completed = Signal(str, bool, str)  # model_name, success, error_message
    download_started = Signal(str)  # model_name
    
    def __init__(self):
        super().__init__()
        self.download_progress: Dict[str, DownloadProgress] = {}
        self.active_downloads: Dict[str, DownloadWorker] = {}
        self.mutex = QMutex()
    
    def get_download_progress(self, model_name: str) -> DownloadProgress:
        """Get download progress for a model"""
        with QMutexLocker(self.mutex):
            if model_name not in self.download_progress:
                self.download_progress[model_name] = DownloadProgress(model_name)
            return self.download_progress[model_name]
    
    def is_downloading(self, model_name: str) -> bool:
        """Check if a model is currently downloading"""
        with QMutexLocker(self.mutex):
            return model_name in self.active_downloads
    
    def start_download(self, config: ModelConfig):
        """Start downloading model weights in background"""
        model_name = config.model_name
        
        with QMutexLocker(self.mutex):
            # Check if already downloading
            if model_name in self.active_downloads:
                return
            
            # Check if already downloaded
            progress = self.get_download_progress(model_name)
            if progress.is_downloaded:
                return
            
            # Start download worker
            worker = DownloadWorker(config)
            worker.progress_updated.connect(self._on_progress_updated)
            worker.download_completed.connect(self._on_download_completed)
            worker.download_started.connect(self._on_download_started)
            
            self.active_downloads[model_name] = worker
            worker.start()
    
    def stop_download(self, model_name: str):
        """Stop downloading a model"""
        with QMutexLocker(self.mutex):
            if model_name in self.active_downloads:
                worker = self.active_downloads[model_name]
                worker.stop()
                worker.wait()
                del self.active_downloads[model_name]
    
    def _on_download_started(self, model_name: str):
        """Handle download started"""
        progress = self.get_download_progress(model_name)
        progress.start_download()
        self.download_started.emit(model_name)
    
    def _on_progress_updated(self, model_name: str, progress_value: float):
        """Handle progress update"""
        progress = self.get_download_progress(model_name)
        progress.update_progress(progress_value)
        self.progress_updated.emit(model_name, progress_value)
    
    def _on_download_completed(self, model_name: str, success: bool, error_message: str):
        """Handle download completion"""
        with QMutexLocker(self.mutex):
            # Remove from active downloads
            if model_name in self.active_downloads:
                del self.active_downloads[model_name]
        
        progress = self.get_download_progress(model_name)
        if success:
            progress.complete_download()
        else:
            progress.fail_download(error_message)
        
        self.download_completed.emit(model_name, success, error_message)
