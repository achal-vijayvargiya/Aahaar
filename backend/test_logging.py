"""
Test script to verify logging is working properly.
Run this to check if logs appear in console and file.
"""
from app.utils.logger import logger

print("\n" + "=" * 70)
print("TESTING LOGGING SYSTEM")
print("=" * 70 + "\n")

# Test different log levels
logger.debug("🔍 This is a DEBUG message - very detailed information")
logger.info("ℹ️  This is an INFO message - general information")
logger.warning("⚠️  This is a WARNING message - something to watch")
logger.error("❌ This is an ERROR message - something went wrong")

print("\n" + "=" * 70)
print("If you see the messages above, logging is working! ✅")
print("=" * 70 + "\n")

# Check log file
import os
from pathlib import Path

log_file = Path("logs/app.log")
if log_file.exists():
    print(f"✅ Log file exists: {log_file.absolute()}")
    print(f"📝 Log file size: {log_file.stat().st_size} bytes")
    
    # Show last few lines
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"\n📄 Last 3 lines from log file:")
        print("-" * 70)
        for line in lines[-3:]:
            print(line.rstrip())
        print("-" * 70)
else:
    print(f"❌ Log file not found: {log_file.absolute()}")

print("\n✅ Logging test complete!\n")

