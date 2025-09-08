#!/usr/bin/env python3
"""
Development Environment Setup Script

This script sets up a complete development environment for the Legal Case File Manager:
1. Creates/resets the PostgreSQL database schema
2. Generates dummy data
3. Applies performance indexes

Usage:
    python setup_dev_environment.py [options]
"""

import argparse
import logging
import os
import subprocess
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_script(script_name, args=None):
    """Run a Python script with optional arguments."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)

    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    logger.info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"[SUCCESS] {script_name} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] {script_name} failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        logger.error(f"[ERROR] {script_name} not found")
        return False


def main():
    parser = argparse.ArgumentParser(description="Setup development environment for Legal Case File Manager")
    parser.add_argument("--client-count", type=int, default=50, help="Number of clients to generate (default: 50)")
    parser.add_argument("--skip-schema", action="store_true", help="Skip database schema setup (use existing schema)")
    parser.add_argument("--skip-data", action="store_true", help="Skip dummy data generation")
    parser.add_argument("--skip-indexes", action="store_true", help="Skip performance index creation")
    parser.add_argument("--host", default="localhost", help="Database host (default: localhost)")
    parser.add_argument("--port", type=int, default=5432, help="Database port (default: 5432)")
    parser.add_argument("--database", default="legal_case_manager", help="Database name (default: legal_case_manager)")
    parser.add_argument("--user", default="postgres", help="Database user (default: postgres)")
    parser.add_argument("--password", default="postgres", help="Database password (default: postgres)")

    args = parser.parse_args()

    print("LEGAL CASE FILE MANAGER - DEVELOPMENT ENVIRONMENT SETUP")
    print("=" * 65)

    success_count = 0
    total_steps = 3

    # Step 1: Database Schema Setup
    if not args.skip_schema:
        print("\n[STEP 1] Setting up database schema...")
        if run_script("database_setup.py"):
            success_count += 1
        else:
            logger.error("Database schema setup failed. Aborting.")
            sys.exit(1)
    else:
        print("\n[STEP 1] Skipping database schema setup (--skip-schema)")
        success_count += 1

    # Step 2: Generate Dummy Data
    if not args.skip_data:
        print("\n[STEP 2] Generating dummy data...")
        data_args = [
            "--clear",
            "--count",
            str(args.client_count),
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--database",
            args.database,
            "--user",
            args.user,
            "--password",
            args.password,
        ]
        if run_script("generate_dummy_data.py", data_args):
            success_count += 1
        else:
            logger.error("Dummy data generation failed. Continuing anyway...")
    else:
        print("\n[STEP 2] Skipping dummy data generation (--skip-data)")
        success_count += 1

    # Step 3: Apply Performance Indexes
    if not args.skip_indexes:
        print("\n[STEP 3] Applying performance indexes...")
        if run_script("add_performance_indexes.py"):
            success_count += 1
        else:
            logger.warning("Performance index setup failed. Application will still work but may be slower.")
    else:
        print("\n[STEP 3] Skipping performance indexes (--skip-indexes)")
        success_count += 1

    # Final Summary
    print("\n" + "=" * 65)
    print("SETUP COMPLETE!")
    print("=" * 65)

    if success_count == total_steps:
        print("[SUCCESS] All setup steps completed successfully!")
        print("\nNEXT STEPS:")
        print("   1. Start the application: python run.py")
        print("   2. Open browser to: http://localhost:5000")
        print("   3. Explore the dashboard and search functionality")
        print("\nWHAT'S AVAILABLE:")
        print(f"   - {args.client_count} clients with realistic data")
        print("   - Associated cases, files, and payments")
        print("   - Full-text search capabilities")
        print("   - Performance-optimized database")

    else:
        print(f"[WARNING] Setup completed with {total_steps - success_count} issue(s)")
        print("   Check the logs above for details")

    print("\nDOCUMENTATION:")
    print("   - README.md - General application info")
    print("   - DUMMY_DATA_GENERATOR.md - Data generation details")

    print("=" * 65)


if __name__ == "__main__":
    main()
