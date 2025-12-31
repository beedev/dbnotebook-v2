"""NLP-based Dashboard Modification Agent.

Allows users to modify dashboard configurations via natural language instructions.
Sends original context + current config + modification instruction to LLM.
"""

import json
import logging
from typing import Optional, List, Tuple, Any
from copy import deepcopy

from .types import (
    DashboardConfig,
    ParsedData,
    ProfilingResult,
    ModificationResult,
)

logger = logging.getLogger(__name__)


# Prompt template for dashboard modification
MODIFICATION_PROMPT_TEMPLATE = """You are an expert data analyst helping modify an interactive analytics dashboard.

## Original Context
{original_context}

## Current Dashboard Configuration
```json
{current_config}
```

## User's Modification Request
{modification_instruction}

## Task
Modify the dashboard configuration based on the user's request. You have FULL authority to:

1. **ADD** new elements:
   - New KPIs (key metrics)
   - New charts (bar, line, pie, scatter, area)
   - New filters (categorical, range, date)

2. **REMOVE** existing elements:
   - Remove KPIs, charts, or filters by not including them in output

3. **EDIT** existing elements:
   - Change chart types, axes, colors
   - Modify KPI aggregations, formats
   - Update filter configurations

4. **REORGANIZE** layout:
   - Change the order of elements

## Guidelines
- Preserve elements the user didn't ask to change
- Use column names from the original data schema
- Validate that referenced columns exist in the data
- Maintain valid configuration structure
- Be creative in interpreting user requests

## Response Format
Return a valid JSON object with the complete modified dashboard configuration:

{{
  "kpis": [...],
  "charts": [...],
  "filters": [...],
  "metadata": {{
    "title": "...",
    "description": "...",
    "recommendationReason": "..."
  }},
  "changes": ["Description of change 1", "Description of change 2", ...]
}}

The "changes" array should describe what was modified in human-readable form.

Return ONLY the JSON object, no additional text."""


class DashboardModifier:
    """NLP-based dashboard modification agent."""

    def __init__(self, llm_provider: Optional[Any] = None):
        """Initialize the modifier.

        Args:
            llm_provider: Optional LLM provider instance.
        """
        self._llm_provider = llm_provider
        self._temperature = 0.0  # Zero temperature for deterministic output
        self._max_tokens = 4000

    def modify(
        self,
        current_config: DashboardConfig,
        instruction: str,
        generation_prompt: str,
        parsed_data: Optional[ParsedData] = None,
    ) -> ModificationResult:
        """Modify dashboard based on natural language instruction.

        Args:
            current_config: Current dashboard configuration
            instruction: User's modification instruction
            generation_prompt: Original generation prompt with data context
            parsed_data: Optional parsed data for column validation

        Returns:
            ModificationResult with new config and changes made
        """
        try:
            # Build the modification prompt
            prompt = self._build_prompt(
                current_config=current_config,
                instruction=instruction,
                original_context=generation_prompt,
            )

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            result = self._parse_response(response, current_config)

            # Validate columns if parsed_data available
            if parsed_data:
                result = self._validate_columns(result, parsed_data)

            logger.info(
                f"Dashboard modified: {len(result.get('changes', []))} changes made"
            )

            return {
                "success": True,
                "dashboard_config": result.get("config"),
                "changes": result.get("changes", []),
                "error": None,
                "can_undo": True,
                "can_redo": False,
            }

        except Exception as e:
            logger.error(f"Error modifying dashboard: {e}")
            return {
                "success": False,
                "dashboard_config": None,
                "changes": [],
                "error": str(e),
                "can_undo": False,
                "can_redo": False,
            }

    def _build_prompt(
        self,
        current_config: DashboardConfig,
        instruction: str,
        original_context: str,
    ) -> str:
        """Build the modification prompt."""
        # Truncate original context if too long (keep first 4000 chars)
        if len(original_context) > 4000:
            original_context = original_context[:4000] + "\n... [truncated]"

        return MODIFICATION_PROMPT_TEMPLATE.format(
            original_context=original_context,
            current_config=json.dumps(current_config, indent=2),
            modification_instruction=instruction,
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM provider with the prompt using deterministic settings."""
        if self._llm_provider is None:
            logger.warning("No LLM provider configured for modification")
            raise ValueError("LLM provider not configured")

        try:
            logger.info(f"Calling LLM for dashboard modification (temp={self._temperature})...")
            # Try to use temperature and max_tokens
            response = self._llm_provider.complete(
                prompt,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            result = response.text if hasattr(response, "text") else str(response)
            logger.info(f"LLM modification response received ({len(result)} chars)")
            return result
        except TypeError:
            # Fallback if the LLM doesn't accept these kwargs directly
            try:
                logger.info("Retrying LLM call without explicit parameters...")
                response = self._llm_provider.complete(prompt)
                result = response.text if hasattr(response, "text") else str(response)
                logger.info(f"LLM modification response received ({len(result)} chars)")
                return result
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                raise
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_response(
        self, response: str, original_config: DashboardConfig
    ) -> dict:
        """Parse and validate the LLM response."""
        # Clean up the response - extract JSON if wrapped in markdown
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            response = "\n".join(lines)

        try:
            result = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Try to find JSON in the response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    result = json.loads(response[start:end])
                except json.JSONDecodeError:
                    raise ValueError("Could not parse modification from LLM response")
            else:
                raise ValueError("No valid JSON found in LLM response")

        # Extract changes list
        changes = result.pop("changes", ["Dashboard modified"])

        # Validate and normalize the config
        config = self._validate_config(result, original_config)

        return {
            "config": config,
            "changes": changes,
        }

    def _validate_config(
        self, config: dict, original_config: DashboardConfig
    ) -> DashboardConfig:
        """Validate and normalize the modified config."""
        # Ensure required keys exist
        if "kpis" not in config:
            config["kpis"] = original_config.get("kpis", [])
        if "charts" not in config:
            config["charts"] = original_config.get("charts", [])
        if "filters" not in config:
            config["filters"] = original_config.get("filters", [])
        if "metadata" not in config:
            config["metadata"] = original_config.get("metadata", {})
        else:
            # Convert snake_case to camelCase in metadata
            metadata = config["metadata"]
            if "recommendation_reason" in metadata:
                metadata["recommendationReason"] = metadata.pop("recommendation_reason")

        # Validate KPIs
        validated_kpis = []
        for i, kpi in enumerate(config.get("kpis", [])):
            if not kpi.get("id"):
                kpi["id"] = f"kpi_{i}"
            if not kpi.get("title"):
                kpi["title"] = kpi.get("metric", f"KPI {i+1}")
            if kpi.get("aggregation") not in ["sum", "avg", "count", "min", "max", "median"]:
                kpi["aggregation"] = "sum"
            if kpi.get("format") not in ["number", "currency", "percentage"]:
                kpi["format"] = "number"
            validated_kpis.append(kpi)
        config["kpis"] = validated_kpis

        # Validate charts (convert snake_case to camelCase)
        validated_charts = []
        for i, chart in enumerate(config.get("charts", [])):
            if not chart.get("id"):
                chart["id"] = f"chart_{i}"
            if not chart.get("title"):
                chart["title"] = f"Chart {i+1}"
            if chart.get("type") not in ["bar", "line", "pie", "scatter", "area"]:
                chart["type"] = "bar"
            # Convert snake_case to camelCase for frontend
            if "x_axis" in chart:
                chart["xAxis"] = chart.pop("x_axis")
            if "y_axis" in chart:
                chart["yAxis"] = chart.pop("y_axis")
            if "allow_cross_filter" in chart:
                chart["allowCrossFilter"] = chart.pop("allow_cross_filter")
            elif "allowCrossFilter" not in chart:
                chart["allowCrossFilter"] = True
            # Handle topN for high-cardinality charts
            if "top_n" in chart:
                chart["topN"] = chart.pop("top_n")
            if "topN" in chart:
                try:
                    chart["topN"] = int(chart["topN"])
                    if chart["topN"] < 1:
                        chart["topN"] = 10
                    elif chart["topN"] > 50:
                        chart["topN"] = 50
                except (ValueError, TypeError):
                    chart["topN"] = 10
            validated_charts.append(chart)
        config["charts"] = validated_charts

        # Validate filters
        validated_filters = []
        for i, filt in enumerate(config.get("filters", [])):
            if not filt.get("id"):
                filt["id"] = f"filter_{i}"
            if not filt.get("label"):
                filt["label"] = filt.get("column", f"Filter {i+1}")
            if filt.get("type") not in ["categorical", "range", "date"]:
                filt["type"] = "categorical"
            validated_filters.append(filt)
        config["filters"] = validated_filters

        return config

    def _validate_columns(
        self, result: dict, parsed_data: ParsedData
    ) -> dict:
        """Validate that referenced columns exist in the data."""
        config = result.get("config", {})
        valid_columns = {col.get("name") for col in parsed_data.get("columns", [])}

        # Check KPI metrics
        for kpi in config.get("kpis", []):
            metric = kpi.get("metric")
            if metric and metric not in valid_columns:
                logger.warning(f"KPI references unknown column: {metric}")
                # Don't remove, but log warning

        # Check chart axes
        for chart in config.get("charts", []):
            x_axis = chart.get("xAxis")
            y_axis = chart.get("yAxis")
            if x_axis and x_axis not in valid_columns:
                logger.warning(f"Chart {chart.get('id')} references unknown x-axis: {x_axis}")
            if y_axis and y_axis not in valid_columns and y_axis != "count":
                logger.warning(f"Chart {chart.get('id')} references unknown y-axis: {y_axis}")

        # Check filter columns
        for filt in config.get("filters", []):
            column = filt.get("column")
            if column and column not in valid_columns:
                logger.warning(f"Filter references unknown column: {column}")

        return result

    def diff_configs(
        self,
        old_config: DashboardConfig,
        new_config: DashboardConfig,
    ) -> List[str]:
        """Generate a list of changes between two configurations."""
        changes = []

        # Compare KPIs
        old_kpi_ids = {k.get("id") for k in old_config.get("kpis", [])}
        new_kpi_ids = {k.get("id") for k in new_config.get("kpis", [])}

        added_kpis = new_kpi_ids - old_kpi_ids
        removed_kpis = old_kpi_ids - new_kpi_ids

        for kpi_id in added_kpis:
            kpi = next((k for k in new_config.get("kpis", []) if k.get("id") == kpi_id), None)
            if kpi:
                changes.append(f"Added KPI: {kpi.get('title', kpi_id)}")

        for kpi_id in removed_kpis:
            kpi = next((k for k in old_config.get("kpis", []) if k.get("id") == kpi_id), None)
            if kpi:
                changes.append(f"Removed KPI: {kpi.get('title', kpi_id)}")

        # Compare Charts
        old_chart_ids = {c.get("id") for c in old_config.get("charts", [])}
        new_chart_ids = {c.get("id") for c in new_config.get("charts", [])}

        added_charts = new_chart_ids - old_chart_ids
        removed_charts = old_chart_ids - new_chart_ids

        for chart_id in added_charts:
            chart = next((c for c in new_config.get("charts", []) if c.get("id") == chart_id), None)
            if chart:
                changes.append(f"Added chart: {chart.get('title', chart_id)} ({chart.get('type', 'unknown')})")

        for chart_id in removed_charts:
            chart = next((c for c in old_config.get("charts", []) if c.get("id") == chart_id), None)
            if chart:
                changes.append(f"Removed chart: {chart.get('title', chart_id)}")

        # Compare Filters
        old_filter_ids = {f.get("id") for f in old_config.get("filters", [])}
        new_filter_ids = {f.get("id") for f in new_config.get("filters", [])}

        added_filters = new_filter_ids - old_filter_ids
        removed_filters = old_filter_ids - new_filter_ids

        for filter_id in added_filters:
            filt = next((f for f in new_config.get("filters", []) if f.get("id") == filter_id), None)
            if filt:
                changes.append(f"Added filter: {filt.get('label', filter_id)}")

        for filter_id in removed_filters:
            filt = next((f for f in old_config.get("filters", []) if f.get("id") == filter_id), None)
            if filt:
                changes.append(f"Removed filter: {filt.get('label', filter_id)}")

        # If no specific changes detected, note general modification
        if not changes:
            changes.append("Dashboard configuration updated")

        return changes
