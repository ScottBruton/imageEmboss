#!/usr/bin/env python3
"""
Check Cached Model Weights
Shows what model weights are already downloaded and cached
"""

import os
from pathlib import Path


def check_cached_weights():
    """Check what model weights are cached"""
    print("🔍 Checking cached model weights...")
    print("=" * 50)
    
    # Check PyTorch cache directory
    torch_cache = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
    
    if not torch_cache.exists():
        print("❌ No PyTorch cache directory found")
        print("   Run the weight downloader to cache model weights")
        return
    
    cached_files = list(torch_cache.glob("*.pth"))
    
    if not cached_files:
        print("❌ No cached weight files found")
        print("   Run the weight downloader to cache model weights")
        return
    
    print(f"✅ Found {len(cached_files)} cached weight files:")
    print()
    
    total_size = 0
    for file in sorted(cached_files):
        size_mb = file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"   📦 {file.name}")
        print(f"      Size: {size_mb:.1f} MB")
        print()
    
    print(f"📊 Total cached size: {total_size:.1f} MB")
    print("🎉 Model weights are cached and ready for fast loading!")


if __name__ == "__main__":
    check_cached_weights()
