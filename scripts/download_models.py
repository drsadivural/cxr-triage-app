#!/usr/bin/env python3
"""
Script to download pretrained models for CXR Triage system.
"""
import os
import sys
import urllib.request
import hashlib
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"

# Model definitions
MODELS = {
    "densenet121-res224-all": {
        "url": "https://github.com/mlmed/torchxrayvision/releases/download/v1/densenet121-res224-all-d3be9be6.pth",
        "filename": "densenet121-res224-all.pth",
        "sha256": "d3be9be6",
        "description": "TorchXRayVision DenseNet121 classifier trained on multiple CXR datasets"
    },
    "densenet121-res224-nih": {
        "url": "https://github.com/mlmed/torchxrayvision/releases/download/v1/densenet121-res224-nih-d3be9be6.pth",
        "filename": "densenet121-res224-nih.pth",
        "sha256": None,
        "description": "TorchXRayVision DenseNet121 classifier trained on NIH ChestX-ray14"
    },
    "densenet121-res224-chex": {
        "url": "https://github.com/mlmed/torchxrayvision/releases/download/v1/densenet121-res224-chex-d3be9be6.pth",
        "filename": "densenet121-res224-chex.pth",
        "sha256": None,
        "description": "TorchXRayVision DenseNet121 classifier trained on CheXpert"
    },
    "densenet121-res224-mimic_nb": {
        "url": "https://github.com/mlmed/torchxrayvision/releases/download/v1/densenet121-res224-mimic_nb-d3be9be6.pth",
        "filename": "densenet121-res224-mimic_nb.pth",
        "sha256": None,
        "description": "TorchXRayVision DenseNet121 classifier trained on MIMIC-CXR"
    },
    "resnet50-res512-all": {
        "url": "https://github.com/mlmed/torchxrayvision/releases/download/v1/resnet50-res512-all-d3be9be6.pth",
        "filename": "resnet50-res512-all.pth",
        "sha256": None,
        "description": "TorchXRayVision ResNet50 classifier (512x512) trained on multiple datasets"
    }
}

def download_file(url: str, dest_path: Path, description: str = ""):
    """Download a file with progress indicator."""
    print(f"\nDownloading: {description or url}")
    print(f"Destination: {dest_path}")
    
    if dest_path.exists():
        print(f"File already exists, skipping...")
        return True
    
    try:
        def progress_hook(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size) if total_size > 0 else 0
            sys.stdout.write(f"\rProgress: {percent}% ({count * block_size / 1024 / 1024:.1f} MB)")
            sys.stdout.flush()
        
        urllib.request.urlretrieve(url, dest_path, progress_hook)
        print("\nDownload complete!")
        return True
    except Exception as e:
        print(f"\nError downloading: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False

def verify_checksum(filepath: Path, expected_hash: str) -> bool:
    """Verify file checksum (partial match)."""
    if not expected_hash:
        return True
    
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    
    actual_hash = sha256.hexdigest()
    return expected_hash in actual_hash

def main():
    """Main function to download all models."""
    print("=" * 60)
    print("CXR Triage - Model Download Script")
    print("=" * 60)
    
    # Create models directory
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nModels directory: {MODELS_DIR}")
    
    # Download models
    success_count = 0
    fail_count = 0
    
    # By default, download only the main model
    models_to_download = ["densenet121-res224-all"]
    
    # Check for --all flag
    if "--all" in sys.argv:
        models_to_download = list(MODELS.keys())
    
    for model_name in models_to_download:
        model_info = MODELS[model_name]
        dest_path = MODELS_DIR / model_info["filename"]
        
        if download_file(
            model_info["url"],
            dest_path,
            model_info["description"]
        ):
            if model_info.get("sha256"):
                if verify_checksum(dest_path, model_info["sha256"]):
                    print("Checksum verified!")
                    success_count += 1
                else:
                    print("WARNING: Checksum mismatch!")
                    fail_count += 1
            else:
                success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"Download Summary: {success_count} succeeded, {fail_count} failed")
    print("=" * 60)
    
    # List downloaded models
    print("\nDownloaded models:")
    for f in MODELS_DIR.glob("*.pth"):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name} ({size_mb:.1f} MB)")
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
