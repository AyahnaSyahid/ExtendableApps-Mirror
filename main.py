"""Jalankan: python main.py"""
import sys
from pathlib import Path

# Tambah root project ke path agar 'myapp' bisa diimport
sys.path.insert(0, str(Path(__file__).parent))

from app.app import main

if __name__ == "__main__":
    main()
