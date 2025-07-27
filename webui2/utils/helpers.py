"""
Utility functions
"""
import pkg_resources
import os


def install_required_packages():
    """Install required packages if missing"""
    required_packages = ["opencc", "transformers", "torch"]
    
    for package in required_packages:
        try:
            pkg_resources.get_distribution(package)
        except pkg_resources.DistributionNotFound:
            print(f"安装缺失的依赖: {package}")
            # Set UV_PYTHON environment variable
            os.environ["UV_PYTHON"] = "F:\\miniconda3\\envs\\index-tts\\python.exe"
            os.system(f"uv pip install {package}")
