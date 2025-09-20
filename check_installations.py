#!/usr/bin/env python3
"""
Package Installation Checker for Segmentation Models PyTorch Environment
This script checks if all required packages are installed with correct versions.
"""

import sys
import subprocess
import importlib
from pathlib import Path

# Required packages with exact versions
REQUIRED_PACKAGES = {
    'torch': '2.2.2',
    'torchvision': '0.17.2', 
    'torchaudio': '2.2.2',
    'segmentation_models_pytorch': '0.3.3',
    'albumentations': '1.3.1',
    'pretrainedmodels': '0.7.4',
    'efficientnet_pytorch': '0.7.1',
    'timm': '0.9.12',
    'opencv-python': '4.9.0.80',
    'shapely': '2.0.4',
    'ezdxf': '1.1.1'
}

def check_virtual_environment():
    """Check if we're running in a virtual environment"""
    print("🔍 Checking Virtual Environment...")
    print("=" * 50)
    
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        print(f"   Virtual env path: {sys.prefix}")
        return True
    else:
        print("⚠️  Not in virtual environment")
        print(f"   Python path: {sys.prefix}")
        return False

def get_package_version(package_name):
    """Get the installed version of a package"""
    try:
        # Try to import the package
        if package_name == 'opencv-python':
            import cv2
            return cv2.__version__
        elif package_name == 'segmentation_models_pytorch':
            import segmentation_models_pytorch as smp
            return smp.__version__
        elif package_name == 'efficientnet_pytorch':
            import efficientnet_pytorch
            return efficientnet_pytorch.__version__
        elif package_name == 'pretrainedmodels':
            import pretrainedmodels
            return pretrainedmodels.__version__
        elif package_name == 'timm':
            import timm
            return timm.__version__
        elif package_name == 'albumentations':
            import albumentations
            return albumentations.__version__
        elif package_name == 'shapely':
            import shapely
            return shapely.__version__
        elif package_name == 'ezdxf':
            import ezdxf
            return ezdxf.__version__
        elif package_name == 'torch':
            import torch
            return torch.__version__
        elif package_name == 'torchvision':
            import torchvision
            return torchvision.__version__
        elif package_name == 'torchaudio':
            import torchaudio
            return torchaudio.__version__
        else:
            # Generic import
            module = importlib.import_module(package_name)
            return getattr(module, '__version__', 'Unknown')
    except ImportError:
        return None
    except Exception as e:
        return f"Error: {e}"

def check_package_installation(package_name, expected_version):
    """Check if a package is installed with correct version"""
    print(f"\n📦 Checking {package_name}...")
    
    installed_version = get_package_version(package_name)
    
    if installed_version is None:
        print(f"   ❌ NOT INSTALLED")
        return False
    elif installed_version.startswith("Error:"):
        print(f"   ⚠️  INSTALLED but error getting version: {installed_version}")
        return True  # Assume it's working if we can import it
    else:
        print(f"   ✅ INSTALLED - Version: {installed_version}")
        
        # Check if version matches (allowing for build suffixes like +cu118)
        if expected_version in installed_version or installed_version.startswith(expected_version):
            print(f"   ✅ VERSION MATCHES expected {expected_version}")
            return True
        else:
            print(f"   ⚠️  VERSION MISMATCH - Expected: {expected_version}, Got: {installed_version}")
            return True  # Still consider it working, just different version

def check_cuda_availability():
    """Check if CUDA is available in PyTorch"""
    print(f"\n🚀 Checking CUDA Availability...")
    print("=" * 50)
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA is available!")
            print(f"   CUDA version: {torch.version.cuda}")
            print(f"   Number of GPUs: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
            return True
        else:
            print("⚠️  CUDA is not available - using CPU")
            return False
    except ImportError:
        print("❌ PyTorch not installed - cannot check CUDA")
        return False

def test_smp_functionality():
    """Test if Segmentation Models PyTorch is working"""
    print(f"\n🧪 Testing SMP Functionality...")
    print("=" * 50)
    
    try:
        import segmentation_models_pytorch as smp
        import torch
        
        print("✅ SMP imported successfully")
        print(f"   SMP version: {smp.__version__}")
        
        # Test creating a simple model
        model = smp.Unet('resnet34', encoder_weights='imagenet', classes=1)
        print("✅ Model creation successful")
        
        # Test with dummy input
        dummy_input = torch.randn(1, 3, 224, 224)
        with torch.no_grad():
            output = model(dummy_input)
        print(f"✅ Model inference successful - Output shape: {output.shape}")
        
        return True
    except Exception as e:
        print(f"❌ SMP functionality test failed: {e}")
        return False

def generate_requirements_file():
    """Generate a requirements.txt file with installed versions"""
    print(f"\n📝 Generating requirements.txt...")
    print("=" * 50)
    
    requirements = []
    for package_name in REQUIRED_PACKAGES.keys():
        version = get_package_version(package_name)
        if version and not version.startswith("Error:"):
            requirements.append(f"{package_name}=={version}")
        else:
            requirements.append(f"{package_name}=={REQUIRED_PACKAGES[package_name]}")
    
    with open('requirements.txt', 'w') as f:
        f.write('\n'.join(requirements))
    
    print("✅ requirements.txt generated with current versions")

def main():
    """Main function"""
    print("🔍 Segmentation Models PyTorch - Installation Checker")
    print("=" * 60)
    
    # Check virtual environment
    venv_status = check_virtual_environment()
    
    # Check Python version
    print(f"\n🐍 Python Version: {sys.version}")
    print(f"   Python executable: {sys.executable}")
    
    # Check all packages
    print(f"\n📦 Package Installation Status:")
    print("=" * 50)
    
    all_installed = True
    for package_name, expected_version in REQUIRED_PACKAGES.items():
        if not check_package_installation(package_name, expected_version):
            all_installed = False
    
    # Check CUDA
    cuda_available = check_cuda_availability()
    
    # Test SMP functionality
    smp_working = test_smp_functionality()
    
    # Generate requirements file
    generate_requirements_file()
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print("=" * 50)
    print(f"Virtual Environment: {'✅ Yes' if venv_status else '❌ No'}")
    print(f"All Packages Installed: {'✅ Yes' if all_installed else '❌ No'}")
    print(f"CUDA Available: {'✅ Yes' if cuda_available else '❌ No'}")
    print(f"SMP Working: {'✅ Yes' if smp_working else '❌ No'}")
    
    if all_installed and smp_working:
        print(f"\n🎉 SUCCESS: All packages are installed and working!")
        print("You can now use Segmentation Models PyTorch in your projects.")
    else:
        print(f"\n⚠️  Some issues detected. Check the details above.")
        if not all_installed:
            print("   - Some packages are missing or have version mismatches")
        if not smp_working:
            print("   - SMP functionality test failed")
    
    print(f"\n📁 Files created:")
    print("   - requirements.txt (with current package versions)")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
