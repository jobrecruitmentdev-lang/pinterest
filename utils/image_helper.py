import os
import shutil
from pathlib import Path
from PIL import Image

def validate_image(image_path: str) -> Path:
    """Check if image exists and is a valid image file."""
    path = Path(image_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Image not found at path: {image_path}")
    
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as e:
        raise ValueError(f"Invalid or corrupted image file: {e}")
    
    return path

def prepare_image_for_account(image_path: str, account_index: int, alter_hash: bool = True) -> str:
    """
    Prepares image file for upload.
    If alter_hash is True, modifies 1 pixel slightly in a temp copy
    so Pinterest doesn't detect identical binary/hash across 7 accounts.
    """
    path = validate_image(image_path)
    if not alter_hash or account_index == 0:
        return str(path)

    temp_dir = path.parent / "temp_prepared_images"
    temp_dir.mkdir(exist_ok=True)
    
    output_path = temp_dir / f"img_acc_{account_index}_{path.name}"
    
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            # Slightly alter bottom-right pixel RGB by +1/-1
            w, h = img.size
            if w > 1 and h > 1:
                r, g, b = img.getpixel((w - 1, h - 1))
                new_r = min(255, max(0, r + (1 if r < 255 else -1)))
                img.putpixel((w - 1, h - 1), (new_r, g, b))
            
            # Save copy with high quality
            img.save(output_path, quality=95, optimize=False)
            return str(output_path)
    except Exception as e:
        print(f"[Warning] Failed to alter image hash ({e}). Using original image.")
        return str(path)

def cleanup_temp_images(image_path: str):
    """Cleans up temp prepared images folder."""
    path = Path(image_path).resolve()
    temp_dir = path.parent / "temp_prepared_images"
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
