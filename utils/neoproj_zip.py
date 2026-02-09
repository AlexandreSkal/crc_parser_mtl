"""
NeoProj ZIP Extraction — safe extraction of NeoProj .zip files.

Handles path traversal protection and Windows drive letter checks.
"""

import os
import re
import shutil
import zipfile


def extract_neoproj_zip(zip_path, dest_dir):
    """
    Safely extract a NeoProj ZIP file.

    Args:
        zip_path: Path to the .zip file
        dest_dir: Destination directory

    Raises:
        ValueError: If zip contains unsafe paths (path traversal)
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            name = member.filename.replace('\\', '/')
            norm = os.path.normpath(name)

            # Security: prevent path traversal
            if os.path.isabs(norm) or norm.startswith('..'):
                raise ValueError(f"Unsafe path in zip: {member.filename}")
            if re.match(r'^[A-Za-z]:', name):
                raise ValueError(f"Unsafe path in zip: {member.filename}")

            target_path = os.path.join(dest_dir, norm)

            if member.is_dir():
                os.makedirs(target_path, exist_ok=True)
                continue

            parent = os.path.dirname(target_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            with zf.open(member, 'r') as src, open(target_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)
