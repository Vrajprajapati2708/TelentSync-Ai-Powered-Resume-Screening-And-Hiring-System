#!/usr/bin/env python3
# ============================================================
#  TalentSync - Application Entry Point
#  Run this file to start the server:
#    py run.py
# ============================================================

import sys
import io
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app import create_app
from app.config.settings import ActiveConfig

app = create_app()

if __name__ == '__main__':
    print("=" * 55)
    print("  TalentSync -- AI Resume Screening System  v2.0")
    print("=" * 55)
    print(f"  Running at:  http://127.0.0.1:{ActiveConfig.PORT}")
    print(f"  Database:   {ActiveConfig.DB_FILE}")
    print(f"  Debug mode: {ActiveConfig.DEBUG}")

    app.run(
        debug=ActiveConfig.DEBUG,
        port=ActiveConfig.PORT,
        host='0.0.0.0'
    )
