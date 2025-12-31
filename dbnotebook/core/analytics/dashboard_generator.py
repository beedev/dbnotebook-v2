"""LLM-powered Dashboard Configuration Generator.

Uses the configured LLM provider to analyze profiling results and
generate intelligent dashboard configurations with KPIs, charts, and filters.
"""

import json
import logging
from typing import Optional, Dict, Any, List

from .types import (
    ParsedData,
    ProfilingResult,
    DashboardConfig,
    KPIConfig,
    ChartConfig,
    FilterConfig,
    DashboardMetadata,
)

logger = logging.getLogger(__name__)


# Prompt template for dashboard generation
DASHBOARD_PROMPT_TEMPLATE = """You are an expert data analyst helping create an interactive analytics dashboard.

## Dataset Overview
- Total Rows: {row_count}
- Total Columns: {column_count}
- Data Quality Score: {quality_score}/10

## Column Metadata
{column_metadata_table}

## Statistical Insights
{profiling_insights}

## Correlations
High correlations detected:
{correlation_list}

## Data Quality Alerts
{quality_alerts}

## Sample Data (First 10 Rows)
{sample_data_json}
{user_requirements_section}
## Task
Based on this analysis, create a comprehensive dashboard configuration with:

1. **KPIs** (3-6 key metrics): Identify the most important numeric metrics to highlight
   - Consider: business relevance, data quality, variance
   - Prefer: aggregations (sum, avg, count), percentages, ratios

2. **Charts** (4-8 visualizations): Recommend chart types based on CARDINALITY

   **CRITICAL Y-AXIS RULES**:
   - **For "Distribution" or "Count" charts**: ALWAYS use y_axis: "count" with aggregation: "count"
     - This counts the NUMBER OF ROWS per category
     - Example: "Location Distribution" → x_axis: Location, y_axis: "count", aggregation: "count"
   - **NEVER use a categorical column as y_axis**: You cannot sum/avg strings!
     - WRONG: y_axis: "Billability_Status" (categorical column) → Results in 0
     - RIGHT: y_axis: "count" (counts rows per x category)
   - **Only use numeric columns as y_axis when summing/averaging actual values**:
     - Example: "Sales by Region" → x_axis: Region, y_axis: "Sales_Amount" (numeric), aggregation: "sum"

   **CRITICAL CARDINALITY RULES** (unique value count in column):
   - **High cardinality (>50 unique values)**: NEVER use bar/pie charts directly
     - Instead: Use "topN" parameter to show only top 10-15 items
   - **Medium cardinality (10-50 unique values)**: Bar chart with topN: 15
   - **Low cardinality (<10 unique values)**: Pie chart or bar chart (full data)

   **Chart Type Guidelines**:
   - Bar Chart: Categorical comparisons (use topN for >10 categories)
   - Line Chart: Time series, trends (datetime on x-axis)
   - Pie Chart: Proportional breakdowns (ONLY for <8 categories)
   - Scatter Plot: Correlations between two numeric variables
   - Area Chart: Cumulative trends over time

3. **Filters** (2-5 dimensions): Suggest interactive filters
   - Categorical with <50 unique values
   - Date ranges for datetime columns
   - Numeric ranges for continuous variables

4. **Cross-Filter Strategy**: Define how filters should cascade

## Response Format
Return a valid JSON object matching this schema:

{{
  "kpis": [
    {{
      "id": "unique_kpi_id",
      "title": "Display Name",
      "metric": "column_name",
      "aggregation": "sum|avg|count|min|max|median",
      "format": "number|currency|percentage",
      "icon": "TrendingUp|DollarSign|Users|BarChart|Activity|Target",
      "color": "blue|green|red|purple|orange"
    }}
  ],
  "charts": [
    {{
      "id": "unique_chart_id",
      "title": "Chart Title",
      "type": "bar|line|pie|scatter|area",
      "x_axis": "column_name",
      "y_axis": "column_name",
      "aggregation": "sum|avg|count|min|max",
      "color": "blue|green|red|purple|orange",
      "allow_cross_filter": true,
      "topN": 10  // Optional: limit to top N items for high-cardinality columns (>10 unique values)
    }}
  ],
  "filters": [
    {{
      "id": "unique_filter_id",
      "column": "column_name",
      "type": "categorical|range|date",
      "label": "Display Label"
    }}
  ],
  "metadata": {{
    "title": "Dashboard Title",
    "description": "Brief description",
    "recommendation_reason": "Why these visualizations?"
  }}
}}

## Guidelines
- **CHECK COLUMN TYPES FIRST**: Look at the "Type" column in metadata:
  - numeric → Can be used as y_axis with sum/avg/min/max
  - categorical → Can ONLY be used as x_axis or for counting (y_axis: "count")
- **CHECK CARDINALITY**: Look at the "Unique" column before choosing chart type
- **FOR DISTRIBUTION CHARTS**: ALWAYS use y_axis: "count", aggregation: "count"
- Prioritize columns with high data quality (low missing %)
- Use correlations to suggest scatter plots
- Recommend time-based charts if datetime columns exist
- **NEVER use pie charts for columns with >8 unique values**
- **NEVER use a categorical column as y_axis** (except "count")
- Ensure at least one filter per major categorical dimension
- Make KPIs actionable and business-relevant
- Return ONLY the JSON object, no additional text"""


class DashboardConfigGenerator:
    """Generates dashboard configurations using LLM analysis."""

    def __init__(self, llm_provider: Optional[Any] = None):
        """Initialize the generator.

        Args:
            llm_provider: Optional LLM provider instance. If None, will
                          try to use the default provider from dbnotebook.
        """
        self._llm_provider = llm_provider
        self._temperature = 0.0  # Zero temperature for deterministic output
        self._max_tokens = 3000

    def generate(
        self,
        parsed_data: ParsedData,
        profiling_result: ProfilingResult,
        title: Optional[str] = None,
        initial_requirements: Optional[str] = None,
    ) -> tuple[DashboardConfig, str]:
        """Generate dashboard configuration from parsed data and profiling.

        Args:
            parsed_data: Parsed Excel/CSV data
            profiling_result: ydata-profiling results
            title: Optional dashboard title
            initial_requirements: Optional user requirements for the dashboard

        Returns:
            Tuple of (DashboardConfig with KPIs, charts, and filters, generation prompt)
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(parsed_data, profiling_result, initial_requirements)

            # Call LLM
            response = self._call_llm(prompt)

            # Parse and validate response
            config = self._parse_response(response)

            # Override title if provided
            if title and config.get("metadata"):
                config["metadata"]["title"] = title

            # If LLM returned empty config, use fallback
            if not config.get('kpis') and not config.get('charts'):
                logger.warning("LLM returned empty config, using fallback generator")
                config = self._generate_fallback_config(parsed_data, profiling_result, title)

            logger.info(
                f"Generated dashboard config: "
                f"{len(config.get('kpis', []))} KPIs, "
                f"{len(config.get('charts', []))} charts, "
                f"{len(config.get('filters', []))} filters"
            )

            return config, prompt

        except Exception as e:
            logger.error(f"Error generating dashboard config: {e}")
            # Return a fallback config
            prompt = self._build_prompt(parsed_data, profiling_result, initial_requirements)
            return self._generate_fallback_config(parsed_data, profiling_result, title), prompt

    def _build_prompt(
        self,
        parsed_data: ParsedData,
        profiling_result: ProfilingResult,
        initial_requirements: Optional[str] = None,
    ) -> str:
        """Build the LLM prompt with all data context."""
        # Column metadata table
        column_table = self._format_column_metadata(parsed_data.get("columns", []))

        # Profiling insights
        insights = self._format_profiling_insights(profiling_result)

        # Correlations
        correlations = self._format_correlations(
            profiling_result.get("correlations", [])
        )

        # Quality alerts
        alerts = self._format_quality_alerts(
            profiling_result.get("quality_alerts", [])
        )

        # Sample data (first 10 rows)
        sample = parsed_data.get("sample_data", [])[:10]
        sample_json = json.dumps(sample, indent=2, default=str)

        # User requirements section
        user_requirements_section = ""
        if initial_requirements and initial_requirements.strip():
            user_requirements_section = f"""

## User Requirements
The user has specified the following requirements for this dashboard:
{initial_requirements}

**IMPORTANT**: Prioritize the user's requirements when designing the dashboard. Focus on visualizations and metrics that address their specific needs while still providing a comprehensive view of the data.

"""

        # Format the prompt
        return DASHBOARD_PROMPT_TEMPLATE.format(
            row_count=parsed_data.get("row_count", 0),
            column_count=parsed_data.get("column_count", 0),
            quality_score=round(profiling_result.get("quality_score", 7.0), 1),
            column_metadata_table=column_table,
            profiling_insights=insights,
            correlation_list=correlations,
            quality_alerts=alerts,
            sample_data_json=sample_json,
            user_requirements_section=user_requirements_section,
        )

    def _format_column_metadata(self, columns: List[Dict]) -> str:
        """Format column metadata as a markdown table."""
        if not columns:
            return "No column metadata available."

        lines = ["| Column | Type | Unique | Null % | Sample Values |", "|--------|------|--------|--------|---------------|"]

        for col in columns:
            name = col.get("name", "")[:20]
            dtype = col.get("inferred_type", "unknown")
            unique = col.get("unique_count", 0)
            null_pct = col.get("null_percent", 0)
            samples = col.get("sample_values", [])[:3]
            sample_str = ", ".join(str(s)[:15] for s in samples)

            lines.append(f"| {name} | {dtype} | {unique} | {null_pct:.1f}% | {sample_str} |")

        return "\n".join(lines)

    def _format_profiling_insights(self, result: ProfilingResult) -> str:
        """Format profiling insights as text."""
        overview = result.get("overview", {})
        if not overview:
            return "No profiling insights available."

        lines = [
            f"- Row count: {overview.get('row_count', 'N/A')}",
            f"- Column count: {overview.get('column_count', 'N/A')}",
            f"- Missing cells: {overview.get('missing_cells_percent', 0):.1f}%",
            f"- Duplicate rows: {overview.get('duplicate_rows_percent', 0):.1f}%",
            f"- Memory size: {overview.get('memory_size', 'N/A')}",
        ]

        # Add column statistics summary
        columns = result.get("columns", [])
        numeric_cols = [c for c in columns if c.get("inferred_type") == "numeric"]
        categorical_cols = [c for c in columns if c.get("inferred_type") == "categorical"]
        datetime_cols = [c for c in columns if c.get("inferred_type") == "datetime"]

        lines.append(f"\nColumn types:")
        lines.append(f"- Numeric columns: {len(numeric_cols)}")
        lines.append(f"- Categorical columns: {len(categorical_cols)}")
        lines.append(f"- Datetime columns: {len(datetime_cols)}")

        return "\n".join(lines)

    def _format_correlations(self, correlations: List[Dict]) -> str:
        """Format correlations as a list."""
        if not correlations:
            return "No significant correlations detected."

        lines = []
        for corr in correlations[:10]:  # Limit to top 10
            var1 = corr.get("var1", "")
            var2 = corr.get("var2", "")
            value = corr.get("correlation", 0)
            lines.append(f"- {var1} <-> {var2}: {value:.2f}")

        return "\n".join(lines)

    def _format_quality_alerts(self, alerts: List[Dict]) -> str:
        """Format quality alerts as a list."""
        if not alerts:
            return "No data quality issues detected."

        lines = []
        for alert in alerts[:10]:  # Limit to top 10
            severity = alert.get("severity", "info")
            column = alert.get("column", "dataset")
            message = alert.get("message", "")
            lines.append(f"- [{severity.upper()}] {column}: {message}")

        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM provider with the prompt using deterministic settings."""
        if self._llm_provider is None:
            logger.warning("No LLM provider configured, using fallback")
            return self._generate_fallback_response(prompt)

        try:
            # Use the configured LLM provider (LlamaIndex style)
            # Set temperature=0 for deterministic output
            logger.info(f"Calling LLM ({type(self._llm_provider).__name__}) for dashboard generation (temp={self._temperature})...")

            # Try to use additional_kwargs for temperature and max_tokens
            # This works with most LlamaIndex LLM providers
            response = self._llm_provider.complete(
                prompt,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            result = response.text if hasattr(response, "text") else str(response)
            logger.info(f"LLM response received ({len(result)} chars)")
            return result
        except TypeError:
            # Fallback if the LLM doesn't accept these kwargs directly
            try:
                logger.info("Retrying LLM call without explicit parameters...")
                response = self._llm_provider.complete(prompt)
                result = response.text if hasattr(response, "text") else str(response)
                logger.info(f"LLM response received ({len(result)} chars)")
                return result
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return self._generate_fallback_response(prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._generate_fallback_response(prompt)

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a simple fallback response when LLM is not available."""
        # Extract some basic info from the prompt for a minimal config
        return json.dumps({
            "kpis": [],
            "charts": [],
            "filters": [],
            "metadata": {
                "title": "Data Dashboard",
                "description": "Auto-generated dashboard",
                "recommendationReason": "Default configuration (LLM not available)"
            }
        })

    def _parse_response(self, response: str) -> DashboardConfig:
        """Parse and validate the LLM response."""
        # Clean up the response - extract JSON if wrapped in markdown
        response = response.strip()
        if response.startswith("```"):
            # Remove markdown code blocks
            lines = response.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            response = "\n".join(lines)

        try:
            config = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Try to find JSON in the response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    config = json.loads(response[start:end])
                except json.JSONDecodeError:
                    raise ValueError("Could not parse dashboard config from LLM response")
            else:
                raise ValueError("No valid JSON found in LLM response")

        # Validate and normalize the config
        return self._validate_config(config)

    def _validate_config(self, config: Dict) -> DashboardConfig:
        """Validate and normalize the dashboard config."""
        # Ensure required keys exist
        if "kpis" not in config:
            config["kpis"] = []
        if "charts" not in config:
            config["charts"] = []
        if "filters" not in config:
            config["filters"] = []
        if "metadata" not in config:
            config["metadata"] = {
                "title": "Dashboard",
                "description": "Auto-generated dashboard"
            }
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
                # Ensure topN is a reasonable integer
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

    def _generate_fallback_config(
        self,
        parsed_data: ParsedData,
        profiling_result: ProfilingResult,
        title: Optional[str] = None,
    ) -> DashboardConfig:
        """Generate a basic fallback config when LLM fails."""
        columns = parsed_data.get("columns", [])

        # Find numeric columns for KPIs
        numeric_cols = [c for c in columns if c.get("inferred_type") == "numeric"]
        categorical_cols = [c for c in columns if c.get("inferred_type") == "categorical"]
        datetime_cols = [c for c in columns if c.get("inferred_type") == "datetime"]

        # Generate basic KPIs from numeric columns
        kpis = []
        for i, col in enumerate(numeric_cols[:4]):
            kpis.append({
                "id": f"kpi_{i}",
                "title": f"Total {col['name']}",
                "metric": col["name"],
                "aggregation": "sum",
                "format": "number",
                "icon": "BarChart",
                "color": ["blue", "green", "purple", "orange"][i % 4]
            })

        # Generate basic charts with cardinality-aware type selection
        charts = []
        chart_idx = 0

        # Bar chart for first categorical column (with topN for high cardinality)
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            unique_count = cat_col.get("unique_count", 0)
            chart_config = {
                "id": f"chart_{chart_idx}",
                "title": f"{numeric_cols[0]['name']} by {cat_col['name']}",
                "type": "bar",
                "xAxis": cat_col["name"],
                "yAxis": numeric_cols[0]["name"],
                "aggregation": "sum",
                "color": "blue",
                "allowCrossFilter": True
            }
            # Add topN for high-cardinality columns
            if unique_count > 10:
                chart_config["topN"] = min(15, unique_count)
            charts.append(chart_config)
            chart_idx += 1

        # Pie chart ONLY for low-cardinality categorical columns (<8 unique values)
        if categorical_cols:
            # Find a low-cardinality column for pie chart
            low_card_col = None
            for col in categorical_cols:
                if col.get("unique_count", 0) <= 8:
                    low_card_col = col
                    break

            if low_card_col:
                charts.append({
                    "id": f"chart_{chart_idx}",
                    "title": f"{low_card_col['name']} Distribution",
                    "type": "pie",
                    "xAxis": low_card_col["name"],
                    "yAxis": "count",
                    "aggregation": "count",
                    "color": "green",
                    "allowCrossFilter": True
                })
                chart_idx += 1
            elif categorical_cols[0].get("unique_count", 0) > 8:
                # High cardinality - use bar chart with topN instead of pie
                charts.append({
                    "id": f"chart_{chart_idx}",
                    "title": f"Top {categorical_cols[0]['name']}s",
                    "type": "bar",
                    "xAxis": categorical_cols[0]["name"],
                    "yAxis": "count",
                    "aggregation": "count",
                    "color": "green",
                    "allowCrossFilter": True,
                    "topN": 10
                })
                chart_idx += 1

        # Line chart if datetime column exists
        if datetime_cols and numeric_cols:
            charts.append({
                "id": f"chart_{chart_idx}",
                "title": f"{numeric_cols[0]['name']} Over Time",
                "type": "line",
                "xAxis": datetime_cols[0]["name"],
                "yAxis": numeric_cols[0]["name"],
                "aggregation": "sum",
                "color": "purple",
                "allowCrossFilter": False
            })
            chart_idx += 1

        # Generate filters from categorical columns
        filters = []
        for i, col in enumerate(categorical_cols[:3]):
            if col.get("unique_count", 0) <= 50:
                filters.append({
                    "id": f"filter_{i}",
                    "column": col["name"],
                    "type": "categorical",
                    "label": col["name"]
                })

        return {
            "kpis": kpis,
            "charts": charts,
            "filters": filters,
            "metadata": {
                "title": title or "Data Dashboard",
                "description": f"Dashboard for {parsed_data.get('file_name', 'dataset')}",
                "recommendationReason": "Auto-generated based on data structure"
            }
        }
