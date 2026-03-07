#!/usr/bin/env python3
"""
FAP Discord Bot - Scraper Directory Cleanup Script

Automatically archives experimental files and updates imports.
Run this from the fap-discord-bot directory.
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime
import json


class ScraperCleanup:
    """Automated cleanup for scraper directory"""

    # Files to KEEP (working files)
    KEEP_FILES = {
        'scraper/__init__.py',
        'scraper/auto_login_feid.py',
        'scraper/flaresolverr_auth.py',
        'scraper/cloudflare.py',
        'scraper/parser.py',
    }

    # Files to ARCHIVE (experimental, unused, or duplicate)
    ARCHIVE_FILES = {
        # Auth modules (not used)
        'scraper/auth.py',
        'scraper/auth_browserless.py',
        'scraper/auth_camoufox.py',
        'scraper/auth_camoufox_final.py',
        'scraper/auth_camoufox_working.py',
        'scraper/auth_nodriver.py',
        'scraper/auth_session_simple.py',
        'scraper/hybrid_auth.py',
        'scraper/persistent_chromium.py',
        'scraper/persistent_profile.py',
        # Utility files
        'scraper/save_session.py',
        'scraper/setup_profile.py',
        'scraper/check_session_duration.py',
        'scraper/use_profile.py',
        # Test files
        'scraper/test_auth.py',
        'scraper/test_camoufox_simple.py',
        'scraper/test_debug.py',
        'scraper/test_session.py',
        'scraper/test_session_auth.py',
        'scraper/test_session_validity.py',
        'scraper/test_simple.py',
        # Root level test files (also archive these)
        'test_fap.py',
        'test_fap_browserless.py',
        'test_parser.py',
        # Documentation files (old guides)
        'FAP-AUTH-COMPARISON.md',
        'FAP-AUTH-COMPLETE-GUIDE.md',
        'FAP-AUTH-SUMMARY.md',
        'PERSISTENT-PROFILE-GUIDE.md',
    }

    # Nested duplicate directory to archive
    ARCHIVE_DIRECTORIES = {
        'fap-discord-bot',  # Nested duplicate
    }

    # Files to update imports
    UPDATE_IMPORTS = {
        'bot/bot.py': {
            'from scraper.auth import FAPAuth': 'from scraper.auto_login_feid import FAPAutoLogin as FAPAuth',
            'self.auth: FAPAuth = None': '# Auth instance will be created when needed',
        },
        'bot/commands/schedule.py': {
            'from ...scraper.auth import FAPAuth': 'from ...scraper.auto_login_feid import FAPAutoLogin as FAPAuth',
        }
    }

    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = Path(root_dir)
        self.dry_run = dry_run
        self.archive_dir = self.root_dir / 'scraper' / 'archive'
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'archived_files': [],
            'kept_files': [],
            'updated_files': [],
            'errors': [],
        }

    def log(self, message: str):
        """Print log message"""
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"{prefix}{message}")

    def create_archive_directory(self):
        """Create archive directory"""
        if self.archive_dir.exists():
            self.log(f"Archive directory exists: {self.archive_dir}")
        else:
            self.log(f"Creating archive directory: {self.archive_dir}")
            if not self.dry_run:
                self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive_file(self, file_path: str):
        """Archive a single file"""
        src = self.root_dir / file_path
        dst = self.archive_dir / Path(file_path).name

        if not src.exists():
            self.log(f"  [SKIP] File not found: {file_path}")
            return

        if dst.exists():
            self.log(f"  [SKIP] Already archived: {file_path}")
            return

        self.log(f"  [ARCHIVE] {file_path}")
        if not self.dry_run:
            shutil.move(str(src), str(dst))

        self.report['archived_files'].append(file_path)

    def archive_directory(self, dir_path: str):
        """Archive an entire directory"""
        src = self.root_dir / dir_path
        dst = self.archive_dir / Path(dir_path).name

        if not src.exists():
            self.log(f"  [SKIP] Directory not found: {dir_path}")
            return

        if dst.exists():
            self.log(f"  [SKIP] Already archived: {dir_path}")
            return

        self.log(f"  [ARCHIVE DIR] {dir_path}/")
        if not self.dry_run:
            shutil.move(str(src), str(dst))

        self.report['archived_files'].append(f"{dir_path}/")

    def verify_keep_files(self):
        """Verify files that should be kept exist"""
        self.log("\n=== Verifying Keep Files ===")
        for file_path in self.KEEP_FILES:
            full_path = self.root_dir / file_path
            if full_path.exists():
                self.log(f"  [OK] {file_path}")
                self.report['kept_files'].append(file_path)
            else:
                self.log(f"  [WARN] Missing: {file_path}")
                self.report['errors'].append(f"Missing expected file: {file_path}")

    def archive_experimental_files(self):
        """Archive all experimental files"""
        self.log("\n=== Archiving Experimental Files ===")
        for file_path in self.ARCHIVE_FILES:
            self.archive_file(file_path)

    def archive_duplicate_directories(self):
        """Archive duplicate/nested directories"""
        self.log("\n=== Archiving Duplicate Directories ===")
        for dir_path in self.ARCHIVE_DIRECTORIES:
            self.archive_directory(dir_path)

    def update_imports(self):
        """Update imports in bot files"""
        self.log("\n=== Updating Imports ===")

        for file_path, replacements in self.UPDATE_IMPORTS.items():
            full_path = self.root_dir / file_path

            if not full_path.exists():
                self.log(f"  [SKIP] File not found: {file_path}")
                continue

            self.log(f"  [UPDATE] {file_path}")

            if self.dry_run:
                # Show what would be changed
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for old, new in replacements.items():
                    if old in content:
                        self.log(f"    - Replace: {old[:60]}...")
                        self.log(f"    + With: {new[:60]}...")
                continue

            # Actually update the file
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                for old, new in replacements.items():
                    content = content.replace(old, new)

                if content != original_content:
                    # Create backup
                    backup_path = full_path.with_suffix('.py.backup')
                    shutil.copy(full_path, backup_path)

                    # Write updated content
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self.log(f"    [BACKUP] Created: {backup_path.name}")
                    self.report['updated_files'].append(file_path)
                else:
                    self.log(f"    [SKIP] No changes needed")

            except Exception as e:
                self.log(f"  [ERROR] Failed to update {file_path}: {e}")
                self.report['errors'].append(f"Failed to update {file_path}: {e}")

    def create_readme(self):
        """Create README in archive directory"""
        readme_content = """# Archived Scraper Files

These files were archived during cleanup on {date}.

## Reason for Archiving

These files were experimental approaches tried during development:
- Alternative authentication methods (Camoufox, Nodriver, etc.)
- Test files and utilities
- Duplicate implementations

## Current Working Solution

The bot now uses:
- `auto_login_feid.py` - Main authentication module (FeID + Playwright)
- `flaresolverr_auth.py` - FlareSolverr integration for Cloudflare bypass
- `parser.py` - HTML parser for schedule data

## Archived Files

{files_list}

## Restore

If you need to restore any file, simply move it back to the parent directory.
""".format(
            date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            files_list='\n'.join(f'- {f}' for f in self.report['archived_files'])
        )

        readme_path = self.archive_dir / 'README.md'
        self.log(f"\n[CREATE] {readme_path}")
        if not self.dry_run:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

    def save_report(self):
        """Save cleanup report"""
        report_path = self.root_dir / 'cleanup_report.json'
        self.log(f"\n[SAVE] Cleanup report: {report_path}")
        if not self.dry_run:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, indent=2)

    def print_summary(self):
        """Print cleanup summary"""
        print("\n" + "=" * 60)
        print("CLEANUP SUMMARY")
        print("=" * 60)
        print(f"Mode:         {'DRY RUN (no changes made)' if self.dry_run else 'LIVE (files modified)'}")
        print(f"Kept files:   {len(self.report['kept_files'])}")
        print(f"Archived:     {len(self.report['archived_files'])}")
        print(f"Updated:      {len(self.report['updated_files'])}")
        print(f"Errors:       {len(self.report['errors'])}")

        if self.report['archived_files']:
            print("\nArchived files:")
            for f in self.report['archived_files']:
                print(f"  - {f}")

        if self.report['updated_files']:
            print("\nUpdated files:")
            for f in self.report['updated_files']:
                print(f"  - {f}")

        if self.report['errors']:
            print("\nErrors:")
            for e in self.report['errors']:
                print(f"  ! {e}")

        print("=" * 60)

    def run(self):
        """Run full cleanup"""
        print("=" * 60)
        print("FAP DISCORD BOT - SCRAPER CLEANUP")
        print("=" * 60)
        print(f"Root directory: {self.root_dir}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print()

        # Step 1: Create archive directory
        self.create_archive_directory()

        # Step 2: Verify keep files
        self.verify_keep_files()

        # Step 3: Archive experimental files
        self.archive_experimental_files()

        # Step 3.5: Archive duplicate directories
        self.archive_duplicate_directories()

        # Step 4: Update imports
        self.update_imports()

        # Step 5: Create README in archive
        self.create_readme()

        # Step 6: Save report
        self.save_report()

        # Step 7: Print summary
        self.print_summary()


def main():
    """Main entry point"""
    import sys

    # Get script directory (where cleanup_scraper.py is located)
    script_dir = Path(__file__).parent.absolute()

    # The script should be in fap-discord-bot directory
    # Check for scraper subdirectory to confirm
    if (script_dir / 'scraper').exists():
        bot_dir = script_dir
    else:
        print("Error: Cannot find scraper directory")
        print(f"Script location: {script_dir}")
        print("Please run this script from the fap-discord-bot directory")
        sys.exit(1)

    # Check for --live flag
    dry_run = '--live' not in sys.argv

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE")
        print("=" * 60)
        print("No changes will be made.")
        print("Use --live flag to apply changes: python cleanup_scraper.py --live")
        print()

    # Run cleanup
    cleanup = ScraperCleanup(bot_dir, dry_run=dry_run)
    cleanup.run()

    # Instructions after dry run
    if dry_run:
        print("\nTo apply these changes, run:")
        print(f"  python {sys.argv[0]} --live")


if __name__ == "__main__":
    main()
