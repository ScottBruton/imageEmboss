"""
Install required packages for ImageEmboss
"""
import subprocess
import sys
import os


def run_command(command):
    """Run a command and return success status"""
    try:
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {command}")
        print(f"   {e.stderr}")
        return False


def install_core_packages():
    """Install core packages"""
    print("📦 Installing core packages...")
    
    packages = [
        "opencv-python>=4.8.0",
        "numpy>=1.21.0",
        "scipy>=1.10.0",
        "ezdxf>=1.1.0",
        "Pillow>=10.0.0",
        "PySide6>=6.5.0"
    ]
    
    for package in packages:
        if not run_command(f"pip install {package}"):
            print(f"⚠️ Failed to install {package}")
    
    print("✅ Core packages installation completed")


def install_performance_packages():
    """Install performance packages"""
    print("🚀 Installing performance packages...")
    
    packages = [
        "numba>=0.57.0"
    ]
    
    for package in packages:
        if not run_command(f"pip install {package}"):
            print(f"⚠️ Failed to install {package}")
    
    print("✅ Performance packages installation completed")


def install_gpu_packages():
    """Install GPU acceleration packages"""
    print("🎮 Installing GPU acceleration packages...")
    
    # Check if CUDA is available
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ NVIDIA GPU detected")
            
            # Install CuPy
            packages = [
                "cupy-cuda12x>=12.0.0"
            ]
            
            for package in packages:
                if not run_command(f"pip install {package}"):
                    print(f"⚠️ Failed to install {package}")
            
            print("✅ GPU packages installation completed")
        else:
            print("⚠️ NVIDIA GPU not detected - skipping GPU packages")
    except Exception as e:
        print(f"⚠️ Error checking GPU: {e}")
        print("⚠️ Skipping GPU packages")


def install_3d_packages():
    """Install 3D visualization packages"""
    print("🎯 Installing 3D visualization packages...")
    
    packages = [
        "PyOpenGL>=3.1.0",
        "PyOpenGL-accelerate>=3.1.0",
        "trimesh>=3.20.0",
        "meshio>=5.3.0"
    ]
    
    for package in packages:
        if not run_command(f"pip install {package}"):
            print(f"⚠️ Failed to install {package}")
    
    print("✅ 3D packages installation completed")


def main():
    """Main installation function"""
    print("🔧 ImageEmboss Package Installer")
    print("=" * 50)
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
    else:
        print("⚠️ Not in a virtual environment - consider using one")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Installation cancelled")
            return
    
    # Install packages
    install_core_packages()
    install_performance_packages()
    install_gpu_packages()
    install_3d_packages()
    
    print("=" * 50)
    print("🎉 Installation completed!")
    print("\nNext steps:")
    print("1. Download FreeCAD from: https://www.freecadweb.org/downloads.php")
    print("2. Run the application: python main.py")
    print("3. Load an image and start processing!")


if __name__ == "__main__":
    main()
