#!/usr/bin/env python3
"""
Auto Download Model Weights
Automatically downloads all model weights without user interaction
"""

import os
import sys
import torch
import segmentation_models_pytorch as smp
from pathlib import Path
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.model_manager import ModelManager


def download_all_weights():
    """Download all model weights automatically"""
    print("🚀 Auto-downloading model weights...")
    print("=" * 50)
    
    model_manager = ModelManager()
    available_models = model_manager.get_available_models()
    
    successful = 0
    failed = 0
    
    for model_name, config in tqdm(available_models.items(), desc="Downloading"):
        try:
            print(f"\n📦 {model_name}...")
            
            # Create model to trigger weight download
            if config.model_type.value == "unet":
                model = smp.Unet(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            elif config.model_type.value == "fpn":
                model = smp.FPN(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            elif config.model_type.value == "pspnet":
                model = smp.PSPNet(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            elif config.model_type.value == "linknet":
                model = smp.Linknet(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            elif config.model_type.value == "pan":
                model = smp.PAN(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            elif config.model_type.value == "manet":
                model = smp.MAnet(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            elif config.model_type.value == "deeplabv3":
                model = smp.DeepLabV3(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            elif config.model_type.value == "deeplabv3plus":
                model = smp.DeepLabV3Plus(
                    encoder_name=config.encoder_name.value,
                    encoder_weights=config.encoder_weights,
                    in_channels=config.in_channels,
                    classes=config.classes,
                    activation=config.activation,
                )
            
            # Test the model with appropriate input size
            # Use larger input size for models that need it
            input_size = 512 if config.model_type.value in ["pspnet", "deeplabv3plus", "pan"] else 224
            dummy_input = torch.randn(1, config.in_channels, input_size, input_size)
            with torch.no_grad():
                _ = model(dummy_input)
            
            print(f"   ✅ Success")
            successful += 1
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 DOWNLOAD COMPLETE")
    print("=" * 50)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Weights cached in: {Path.home() / '.cache' / 'torch' / 'hub' / 'checkpoints'}")
    print("🎉 All model weights are now cached for faster loading!")


if __name__ == "__main__":
    download_all_weights()
