"""
web-core — Ring-based web access architecture.

Ring 0 (HTTP):     httpx + stdlib — always available
Ring 1 (Browser):  Playwright — available if installed
Ring 2 (CLI):      bb-browser/opencli — available if binaries found
Ring 3 (Pipeline): Multi-source research — available if R0+R1 available
"""
__version__ = "1.0.0"
