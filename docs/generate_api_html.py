#!/usr/bin/env python
"""Generate HTML API documentation using pdoc."""

import subprocess
import shutil
from pathlib import Path

def generate_api_docs():
    """Generate HTML API documentation using pdoc."""
    # Define paths
    docs_dir = Path(__file__).parent
    output_dir = docs_dir / "api_html"

    # Clean existing documentation if it exists
    if output_dir.exists():
        print(f"Removing existing documentation at {output_dir}")
        shutil.rmtree(output_dir)

    # Generate new documentation
    print("Generating HTML API documentation with pdoc...")
    cmd = [
        "pdoc",
        "-o", str(output_dir),
        "--no-show-source",
        "--footer-text", "teval API Documentation",
        "teval"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error generating documentation:\n{result.stderr}")
        return False

    print(f"✅ Documentation generated successfully at {output_dir}/")
    print(f"   Open {output_dir}/index.html in your browser to view.")

    return True

if __name__ == "__main__":
    success = generate_api_docs()
    exit(0 if success else 1)