"""Packaged entry point for the Host-owned image production gate."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
from drama_plugin.visual import production
from drama_plugin.hosts.comfy_video import verify_execution

production.video_verifier = verify_execution

if __name__ == '__main__':
    production.main()
