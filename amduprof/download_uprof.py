#!/usr/bin/env python3
"""
Automated AMD uProf downloader via Playwright.

AMD gates the download behind a JavaScript EULA acceptance page.
This script automates the browser interaction:
  1. Navigate to the AMD uProf download page
  2. Find and click the Linux x64 download link
  3. Accept the EULA in the popup/page
  4. Wait for the download to complete
  5. Rename from UUID to AMDuProf_Linux_x64_VERSION.tar.bz2

Usage:
    python download_uprof.py [--version 5.2.606] [--output-dir .]

The downloaded file will be named AMDuProf_Linux_x64_VERSION.tar.bz2
and can be used directly by the PKGBUILD.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time


def find_download(download_dir, timeout=300):
    """Wait for a large bzip2 file to appear in the download directory."""
    start = time.time()
    while time.time() - start < timeout:
        # Check for new large files
        for f in glob.glob(os.path.join(download_dir, "*")):
            size = os.path.getsize(f)
            if size > 100_000_000:  # > 100MB
                # Verify it's bzip2
                result = subprocess.run(["file", f], capture_output=True, text=True)
                if "bzip2" in result.stdout:
                    return f
        time.sleep(2)
    return None


def download_with_playwright(version, output_dir):
    """Use Playwright to navigate AMD EULA and download."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install")
        sys.exit(1)

    target_name = f"AMDuProf_Linux_x64_{version}.tar.bz2"
    target_path = os.path.join(output_dir, target_name)

    if os.path.exists(target_path):
        print(f"Already exists: {target_path}")
        return target_path

    print(f"Downloading AMD uProf {version} via Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible for EULA
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # Navigate to the download URL (will redirect to EULA)
        url = f"https://download.amd.com/developer/eula/uprof/AMDuProf_Linux_x64_{version}.tar.bz2"
        print(f"  Navigating to {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Wait for user to accept EULA (manual step -- AMD's JS is complex)
        print("  Waiting for EULA acceptance and download...")
        print("  (If a browser window appeared, accept the EULA to start download)")

        # Wait for download event
        with page.expect_download(timeout=300000) as download_info:
            # Try to find and click an accept/download button
            for selector in [
                "button:has-text('Accept')",
                "a:has-text('Download')",
                "button:has-text('I Accept')",
                "input[type='submit']",
                "#download-button",
            ]:
                try:
                    el = page.query_selector(selector)
                    if el:
                        print(f"  Found button: {selector}")
                        el.click()
                        break
                except Exception:
                    continue

        download = download_info.value
        print(f"  Download started: {download.suggested_filename}")

        # Save to target path
        download.save_as(target_path)
        print(f"  Saved: {target_path} ({os.path.getsize(target_path) / 1024 / 1024:.0f} MB)")

        browser.close()

    return target_path


def find_in_playwright_artifacts(version, output_dir):
    """Check if the file was already downloaded by a previous Playwright session."""
    artifact_dirs = glob.glob("/tmp/playwright-artifacts-*")
    for d in artifact_dirs:
        for f in glob.glob(os.path.join(d, "*")):
            try:
                size = os.path.getsize(f)
                if size > 100_000_000:
                    result = subprocess.run(["file", f], capture_output=True, text=True)
                    if "bzip2" in result.stdout:
                        # Verify it's uProf by checking contents
                        check = subprocess.run(
                            ["tar", "tjf", f],
                            capture_output=True, text=True, timeout=10,
                        )
                        if f"AMDuProf_Linux_x64_{version}" in check.stdout:
                            target = os.path.join(output_dir, f"AMDuProf_Linux_x64_{version}.tar.bz2")
                            shutil.copy2(f, target)
                            print(f"Found in playwright artifacts: {f}")
                            print(f"Copied to: {target}")
                            return target
            except Exception:
                continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Download AMD uProf via Playwright EULA automation")
    parser.add_argument("--version", default="5.2.606", help="uProf version")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--check-artifacts", action="store_true",
                        help="Check playwright-artifacts for already-downloaded file")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    target = os.path.join(output_dir, f"AMDuProf_Linux_x64_{args.version}.tar.bz2")

    if os.path.exists(target):
        print(f"Already exists: {target}")
        return

    # Strategy 1: Check playwright artifacts from previous sessions
    if args.check_artifacts:
        found = find_in_playwright_artifacts(args.version, output_dir)
        if found:
            return

    # Strategy 2: Automate via Playwright
    download_with_playwright(args.version, output_dir)


if __name__ == "__main__":
    main()
