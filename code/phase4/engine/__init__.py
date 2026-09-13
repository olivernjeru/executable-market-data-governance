# SIMULATED RESEARCH ARTIFACT -- NOT A TRADING SYSTEM.
"""
  This code is not connected to, endorsed by, or representative of any exchange, broker, depository, regulator or trading venue, and it does not execute, route or settle orders. Nothing here is legal, financial, tax, accounting or investment advice. Fee, calendar, settlement and price-limit values are approximations compiled by the authors from public sources for academic use. They are NOT official data and have NOT been verified against the instruments they approximate. Do not rely on them for any real-world purpose. See README.md (Provenance and attribution) for what each class of value approximates.

Market Simulation Engine - Core Components (Research Code Snapshot)
"""

from .fees import FeeEngine
from .loader import *
from .resolver import *

__all__ = ['FeeEngine']
