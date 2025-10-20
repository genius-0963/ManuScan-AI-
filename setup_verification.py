#!/usr/bin/env python3
"""
ManuScan AI - Setup Verification Script
Checks if all dependencies and components are properly installed
"""

import sys
import importlib
from pathlib import Path
from typing import List, Tuple


class SetupVerifier:
    """Verify ManuScan AI installation"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
    
    def check_python_version(self) -> bool:
        """Check Python version >= 3.9"""
        print("Checking Python version...", end=" ")
        version = sys.version_info
        if version.major >= 3 and version.minor >= 9:
            print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.9+)")
            self.issues.append("Python version too old")
            return False
    
    def check_package(self, package_name: str, import_name: str = None) -> bool:
        """Check if a Python package is installed"""
        if import_name is None:
            import_name = package_name
        
        try:
            mod = importlib.import_module(import_name)
            version = getattr(mod, '__version__', 'unknown')
            print(f"  ✓ {package_name} ({version})")
            return True
        except ImportError:
            print(f"  ✗ {package_name} (not installed)")
            self.issues.append(f"Missing package: {package_name}")
            return False
    
    def check_python_packages(self) -> bool:
        """Check all required Python packages"""
        print("\nChecking Python packages...")
        
        packages = [
            ('torch', 'torch'),
            ('torch-geometric', 'torch_geometric'),
            ('open3d', 'open3d'),
            ('numpy', 'numpy'),
            ('scipy', 'scipy'),
            ('tensorflowjs', 'tensorflowjs'),
            ('trimesh', 'trimesh'),
            ('loguru', 'loguru'),
            ('tqdm', 'tqdm'),
        ]
        
        all_installed = True
        for package_name, import_name in packages:
            if not self.check_package(package_name, import_name):
                all_installed = False
        
        return all_installed
    
    def check_cuda(self) -> bool:
        """Check CUDA availability"""
        print("\nChecking CUDA/GPU support...", end=" ")
        
        try:
            import torch
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                device_name = torch.cuda.get_device_name(0)
                print(f"✓ CUDA available ({device_count} device(s))")
                print(f"  Device: {device_name}")
                return True
            else:
                print("⚠ CUDA not available (will use CPU)")
                self.warnings.append("GPU not available - training will be slower")
                return False
        except:
            print("⚠ Cannot check CUDA")
            return False
    
    def check_directory_structure(self) -> bool:
        """Check if required directories exist"""
        print("\nChecking directory structure...")
        
        required_dirs = [
            'backend',
            'backend/geometry',
            'backend/models',
            'backend/export',
            'frontend',
            'frontend/src',
            'frontend/src/core',
            'frontend/src/visualization',
            'scripts',
            'docs',
        ]
        
        all_exist = True
        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists():
                print(f"  ✓ {dir_path}/")
            else:
                print(f"  ✗ {dir_path}/ (missing)")
                self.issues.append(f"Missing directory: {dir_path}")
                all_exist = False
        
        return all_exist
    
    def check_key_files(self) -> bool:
        """Check if key files exist"""
        print("\nChecking key files...")
        
        key_files = [
            'README.md',
            'requirements.txt',
            'package.json',
            'backend/geometry/mesh_processor.py',
            'backend/geometry/feature_detection.py',
            'backend/models/gnn_architecture.py',
            'backend/models/training.py',
            'frontend/src/core/engine.ts',
            'frontend/src/visualization/viewer.ts',
            'frontend/index.html',
        ]
        
        all_exist = True
        for file_path in key_files:
            path = Path(file_path)
            if path.exists():
                size = path.stat().st_size
                print(f"  ✓ {file_path} ({size:,} bytes)")
            else:
                print(f"  ✗ {file_path} (missing)")
                self.issues.append(f"Missing file: {file_path}")
                all_exist = False
        
        return all_exist
    
    def check_node_modules(self) -> bool:
        """Check if Node.js dependencies are installed"""
        print("\nChecking Node.js setup...")
        
        node_modules = Path('frontend/node_modules')
        package_lock = Path('frontend/package-lock.json')
        
        if node_modules.exists():
            print(f"  ✓ node_modules/ installed")
            return True
        else:
            print(f"  ⚠ node_modules/ not found")
            if package_lock.exists():
                print(f"  → Run: cd frontend && npm install")
            else:
                print(f"  → Run: cd frontend && npm install")
            self.warnings.append("Node.js dependencies not installed")
            return False
    
    def test_imports(self) -> bool:
        """Test importing backend modules"""
        print("\nTesting backend imports...")
        
        test_imports = [
            'backend.geometry.mesh_processor',
            'backend.geometry.feature_detection',
            'backend.geometry.graph_converter',
            'backend.models.gnn_architecture',
        ]
        
        all_successful = True
        for module_name in test_imports:
            try:
                importlib.import_module(module_name)
                print(f"  ✓ {module_name}")
            except Exception as e:
                print(f"  ✗ {module_name}: {str(e)}")
                self.issues.append(f"Cannot import: {module_name}")
                all_successful = False
        
        return all_successful
    
    def create_missing_dirs(self):
        """Create missing directories"""
        print("\nCreating missing directories...")
        
        dirs_to_create = [
            'backend/data/raw',
            'backend/data/processed',
            'backend/data/annotations',
            'checkpoints',
            'logs',
            'frontend/public/models',
            'frontend/public/wasm',
        ]
        
        for dir_path in dirs_to_create:
            path = Path(dir_path)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                print(f"  ✓ Created {dir_path}/")
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        
        if not self.issues and not self.warnings:
            print("✅ All checks passed! ManuScan AI is ready to use.")
            print("\nNext steps:")
            print("  1. Train model: ./scripts/train_model.sh")
            print("  2. Start frontend: cd frontend && npm run dev")
            print("  3. Run examples: python example_usage.py")
        else:
            if self.issues:
                print(f"\n❌ Issues found ({len(self.issues)}):")
                for issue in self.issues:
                    print(f"  - {issue}")
            
            if self.warnings:
                print(f"\n⚠️  Warnings ({len(self.warnings)}):")
                for warning in self.warnings:
                    print(f"  - {warning}")
            
            print("\nTo fix issues:")
            print("  1. Install Python packages: pip install -r requirements.txt")
            print("  2. Install Node packages: cd frontend && npm install")
            print("  3. Check Python version: python --version")
        
        print("=" * 60)
    
    def run(self):
        """Run all verification checks"""
        print("=" * 60)
        print("ManuScan AI - Setup Verification")
        print("=" * 60)
        
        # Run checks
        self.check_python_version()
        self.check_python_packages()
        self.check_cuda()
        self.check_directory_structure()
        self.check_key_files()
        self.check_node_modules()
        
        # Try imports
        if not self.issues:
            self.test_imports()
        
        # Create missing directories
        self.create_missing_dirs()
        
        # Print summary
        self.print_summary()
        
        return len(self.issues) == 0


def main():
    """Main entry point"""
    verifier = SetupVerifier()
    success = verifier.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
