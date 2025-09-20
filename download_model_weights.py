#!/usr/bin/env python3
"""
Model Weights Downloader
Downloads all model weights in advance for faster loading
"""

import os
import sys
import torch
import segmentation_models_pytorch as smp
from pathlib import Path
import time
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.model_manager import ModelManager, ModelType, EncoderType


class ModelWeightsDownloader:
    """Downloads and caches model weights"""
    
    def __init__(self, cache_dir: str = "model_weights"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.model_manager = ModelManager()
        
        # Track download progress
        self.downloaded = 0
        self.total = 0
        self.failed = []
        self.successful = []
    
    def download_all_weights(self):
        """Download weights for all available models"""
        print("🚀 Starting model weights download...")
        print(f"📁 Cache directory: {self.cache_dir.absolute()}")
        print("=" * 60)
        
        available_models = self.model_manager.get_available_models()
        self.total = len(available_models)
        
        for model_name, config in tqdm(available_models.items(), desc="Downloading models"):
            print(f"\n📦 Downloading: {model_name}")
            success = self._download_model_weights(config)
            
            if success:
                self.successful.append(model_name)
                print(f"✅ Success: {model_name}")
            else:
                self.failed.append(model_name)
                print(f"❌ Failed: {model_name}")
        
        self._print_summary()
    
    def _download_model_weights(self, config) -> bool:
        """Download weights for a specific model configuration"""
        try:
            # Create model to trigger weight download
            model = self._create_model(config)
            
            # The weights are automatically downloaded when creating the model
            # We just need to ensure they're cached properly
            
            # Test that the model works
            dummy_input = torch.randn(1, config.in_channels, 224, 224)
            with torch.no_grad():
                _ = model(dummy_input)
            
            return True
            
        except Exception as e:
            print(f"   Error: {str(e)}")
            return False
    
    def _create_model(self, config):
        """Create a model (same logic as ModelManager)"""
        model_type = config.model_type.value
        encoder_name = config.encoder_name.value
        
        if model_type == "unet":
            return smp.Unet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "fpn":
            return smp.FPN(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "pspnet":
            return smp.PSPNet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "linknet":
            return smp.Linknet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "pan":
            return smp.PAN(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "manet":
            return smp.MAnet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "deeplabv3":
            return smp.DeepLabV3(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "deeplabv3plus":
            return smp.DeepLabV3Plus(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def _print_summary(self):
        """Print download summary"""
        print("\n" + "=" * 60)
        print("📊 DOWNLOAD SUMMARY")
        print("=" * 60)
        print(f"✅ Successful: {len(self.successful)}/{self.total}")
        print(f"❌ Failed: {len(self.failed)}/{self.total}")
        
        if self.successful:
            print("\n✅ Successfully downloaded:")
            for model in self.successful:
                print(f"   • {model}")
        
        if self.failed:
            print("\n❌ Failed to download:")
            for model in self.failed:
                print(f"   • {model}")
        
        print(f"\n📁 Weights cached in: {self.cache_dir.absolute()}")
        print("🎉 Download complete! Models will now load faster.")
    
    def check_cache_status(self):
        """Check which weights are already cached"""
        print("🔍 Checking cached model weights...")
        
        # Check PyTorch cache directory
        torch_cache = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
        if torch_cache.exists():
            cached_files = list(torch_cache.glob("*.pth"))
            print(f"📁 Found {len(cached_files)} cached weight files:")
            for file in cached_files:
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"   • {file.name} ({size_mb:.1f} MB)")
        else:
            print("📁 No cached weights found")
    
    def clear_cache(self):
        """Clear all cached weights"""
        print("🗑️ Clearing model weight cache...")
        
        # Clear PyTorch cache
        torch_cache = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
        if torch_cache.exists():
            for file in torch_cache.glob("*.pth"):
                file.unlink()
                print(f"   Deleted: {file.name}")
        
        # Clear local cache
        if self.cache_dir.exists():
            for file in self.cache_dir.glob("*"):
                file.unlink()
                print(f"   Deleted: {file.name}")
        
        print("✅ Cache cleared!")


def main():
    """Main function"""
    downloader = ModelWeightsDownloader()
    
    print("🤖 Model Weights Downloader")
    print("=" * 40)
    print("1. Download all model weights")
    print("2. Check cache status")
    print("3. Clear cache")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "1":
                downloader.download_all_weights()
            elif choice == "2":
                downloader.check_cache_status()
            elif choice == "3":
                confirm = input("Are you sure you want to clear the cache? (y/N): ").strip().lower()
                if confirm == 'y':
                    downloader.clear_cache()
            elif choice == "4":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1-4.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
