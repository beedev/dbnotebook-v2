"""Analytics module for Excel data profiling and dashboard generation.

Provides:
- Excel/CSV file parsing with pandas
- Statistical profiling with ydata-profiling
- LLM-powered dashboard configuration generation
- NLP-driven dashboard modification
"""

from .types import (
    ColumnMetadata,
    ParsedData,
    ProfilingResult,
    DashboardConfig,
    KPIConfig,
    ChartConfig,
    FilterConfig,
    AnalysisSession,
    ModificationResult,
)
from .service import AnalyticsService
from .profiler import DataProfiler
from .dashboard_generator import DashboardConfigGenerator
from .dashboard_modifier import DashboardModifier

__all__ = [
    # Types
    "ColumnMetadata",
    "ParsedData",
    "ProfilingResult",
    "DashboardConfig",
    "KPIConfig",
    "ChartConfig",
    "FilterConfig",
    "AnalysisSession",
    "ModificationResult",
    # Services
    "AnalyticsService",
    "DataProfiler",
    "DashboardConfigGenerator",
    "DashboardModifier",
]
