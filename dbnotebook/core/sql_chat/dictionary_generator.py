"""
Dictionary Generator for SQL Chat.

Generates human-readable Markdown dictionaries from database schemas.
These dictionaries are stored as notebook sources and indexed via RAG
for context retrieval during SQL generation.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from dbnotebook.core.sql_chat.types import (
    ColumnInfo,
    ForeignKey,
    SchemaInfo,
    TableInfo,
)

logger = logging.getLogger(__name__)


class InferredRelationship:
    """Represents an inferred foreign key relationship."""

    def __init__(
        self,
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        confidence: float,
        inference_method: str
    ):
        self.from_table = from_table
        self.from_column = from_column
        self.to_table = to_table
        self.to_column = to_column
        self.confidence = confidence
        self.inference_method = inference_method


class DictionaryGenerator:
    """Generate Markdown dictionary documents from database schemas.

    Features:
    - Human-readable Markdown format
    - Inferred relationships from naming conventions
    - Sample values for context
    - Placeholders for human descriptions
    - Schema metadata for RAG retrieval
    """

    # Common ID suffixes for relationship inference
    ID_SUFFIXES = ['_id', 'id', '_key', '_fk', '_ref']

    # Common table name patterns to singularize
    PLURAL_ENDINGS = {
        'ies': 'y',      # categories -> category
        'es': '',        # statuses -> status
        's': '',         # users -> user
    }

    def __init__(self):
        """Initialize dictionary generator."""
        pass

    def generate_dictionary(
        self,
        schema: SchemaInfo,
        connection_name: str,
        include_samples: bool = True,
        include_inferred: bool = True
    ) -> str:
        """Generate Markdown dictionary from schema.

        Args:
            schema: Database schema information
            connection_name: Human-readable connection name
            include_samples: Include sample values in dictionary
            include_inferred: Include inferred relationships

        Returns:
            Markdown formatted dictionary document
        """
        lines = []

        # Header
        lines.append(f"# Database Dictionary: {connection_name}")
        lines.append("")
        lines.append(f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Database**: {schema.database_name or 'unknown'}")
        lines.append(f"**Tables**: {len(schema.tables)}")
        lines.append("")

        # Overview section
        lines.append("## Overview")
        lines.append("")
        lines.append("This dictionary describes the database schema for natural language to SQL translation.")
        lines.append("Edit descriptions and notes to improve query accuracy.")
        lines.append("")

        # Table of Contents
        lines.append("## Table of Contents")
        lines.append("")
        for table in sorted(schema.tables, key=lambda t: t.name):
            lines.append(f"- [{table.name}](#{table.name.lower().replace('_', '-')})")
        lines.append("")

        # Tables section
        lines.append("## Tables")
        lines.append("")

        for table in sorted(schema.tables, key=lambda t: t.name):
            lines.extend(self._format_table(table, schema, include_samples))
            lines.append("")

        # Relationships section
        lines.append("## Relationships")
        lines.append("")

        # Explicit foreign keys
        if schema.relationships:
            lines.append("### Defined Foreign Keys")
            lines.append("")
            for rel in schema.relationships:
                lines.append(f"- **{rel.from_table}.{rel.from_column}** → {rel.to_table}.{rel.to_column}")
            lines.append("")

        # Inferred relationships
        if include_inferred:
            inferred = self.infer_relationships(schema)
            if inferred:
                lines.append("### Inferred Relationships")
                lines.append("")
                lines.append("*These relationships are inferred from naming conventions. Please verify and add to explicit FKs if correct.*")
                lines.append("")
                for inf in inferred:
                    confidence_stars = "★" * int(inf.confidence * 5)
                    lines.append(
                        f"- **{inf.from_table}.{inf.from_column}** → {inf.to_table}.{inf.to_column} "
                        f"({inf.inference_method}, {confidence_stars})"
                    )
                lines.append("")

        # Common query patterns section (placeholder for learning)
        lines.append("## Common Query Patterns")
        lines.append("")
        lines.append("*Add common query patterns here to improve SQL generation accuracy.*")
        lines.append("")
        lines.append("### Example Patterns")
        lines.append("")
        lines.append("```")
        lines.append("# Example: Get all orders for a customer")
        lines.append("# Tables: orders JOIN customers ON orders.customer_id = customers.id")
        lines.append("# Use case: Customer order history lookup")
        lines.append("```")
        lines.append("")

        # Business glossary section
        lines.append("## Business Glossary")
        lines.append("")
        lines.append("*Add business term definitions here to help with natural language understanding.*")
        lines.append("")
        lines.append("| Term | Definition | Related Tables |")
        lines.append("|------|------------|----------------|")
        lines.append("| [Add term] | [Add definition] | [Add tables] |")
        lines.append("")

        # Notes section
        lines.append("## Notes")
        lines.append("")
        lines.append("- Edit this document to add descriptions, business context, and query patterns")
        lines.append("- The RAG engine will use this content to improve SQL generation accuracy")
        lines.append("- Changes will be preserved during schema sync (only new tables/columns added)")
        lines.append("")

        return "\n".join(lines)

    def _format_table(
        self,
        table: TableInfo,
        schema: SchemaInfo,
        include_samples: bool
    ) -> List[str]:
        """Format a single table as Markdown.

        Args:
            table: Table information
            schema: Full schema for relationship lookup
            include_samples: Include sample values

        Returns:
            List of Markdown lines
        """
        lines = []

        # Table header with row count
        row_info = f" (~{table.row_count:,} rows)" if table.row_count else ""
        lines.append(f"### {table.name}{row_info}")
        lines.append("")

        # Table description placeholder
        lines.append(f"**Description**: [Add description for {table.name}]")
        lines.append("")

        # Column table
        lines.append("| Column | Type | Constraints | Description |")
        lines.append("|--------|------|-------------|-------------|")

        for col in table.columns:
            constraints = self._get_column_constraints(col)
            desc = f"[Add description]"
            if col.comment:
                desc = col.comment
            lines.append(f"| {col.name} | {col.type} | {constraints} | {desc} |")

        lines.append("")

        # Sample values
        if include_samples and table.sample_values:
            lines.append("**Sample Values**:")
            lines.append("")
            for col_name, values in list(table.sample_values.items())[:5]:
                # Format values, truncating long strings
                formatted_values = []
                for v in values[:3]:
                    s = str(v)
                    if len(s) > 30:
                        s = s[:27] + "..."
                    formatted_values.append(s)
                lines.append(f"- `{col_name}`: {', '.join(formatted_values)}")
            lines.append("")

        return lines

    def _get_column_constraints(self, col: ColumnInfo) -> str:
        """Get formatted constraint string for a column.

        Args:
            col: Column information

        Returns:
            Constraint string
        """
        constraints = []
        if col.primary_key:
            constraints.append("PK")
        if col.foreign_key:
            constraints.append(f"FK→{col.foreign_key}")
        if not col.nullable:
            constraints.append("NOT NULL")
        return " ".join(constraints) if constraints else "-"

    def infer_relationships(
        self,
        schema: SchemaInfo,
        min_confidence: float = 0.5
    ) -> List[InferredRelationship]:
        """Infer relationships from naming conventions.

        Args:
            schema: Database schema
            min_confidence: Minimum confidence threshold

        Returns:
            List of inferred relationships
        """
        inferred = []
        table_names = {t.name.lower() for t in schema.tables}

        # Build set of existing explicit FKs to avoid duplicates
        existing_fks: Set[Tuple[str, str, str, str]] = set()
        for rel in schema.relationships:
            existing_fks.add((
                rel.from_table.lower(),
                rel.from_column.lower(),
                rel.to_table.lower(),
                rel.to_column.lower()
            ))

        for table in schema.tables:
            for col in table.columns:
                # Skip primary keys and existing FKs
                if col.primary_key:
                    continue
                if col.foreign_key:
                    continue

                # Check for ID suffix patterns
                col_lower = col.name.lower()
                for suffix in self.ID_SUFFIXES:
                    if col_lower.endswith(suffix):
                        # Extract potential table name
                        prefix = col_lower[:-len(suffix)]
                        if not prefix:
                            continue

                        # Try to find matching table
                        target_table, confidence, method = self._find_target_table(
                            prefix, table_names, table.name.lower()
                        )

                        if target_table and confidence >= min_confidence:
                            # Check not already explicit FK
                            fk_key = (
                                table.name.lower(),
                                col.name.lower(),
                                target_table,
                                'id'
                            )
                            if fk_key not in existing_fks:
                                inferred.append(InferredRelationship(
                                    from_table=table.name,
                                    from_column=col.name,
                                    to_table=target_table,
                                    to_column='id',
                                    confidence=confidence,
                                    inference_method=method
                                ))
                        break

        # Sort by confidence descending
        inferred.sort(key=lambda x: x.confidence, reverse=True)
        return inferred

    def _find_target_table(
        self,
        prefix: str,
        table_names: Set[str],
        source_table: str
    ) -> Tuple[Optional[str], float, str]:
        """Find target table for a column prefix.

        Args:
            prefix: Column name prefix (e.g., 'customer' from 'customer_id')
            table_names: Set of lowercase table names
            source_table: Source table name to exclude

        Returns:
            Tuple of (target_table, confidence, inference_method)
        """
        # Skip self-references
        if prefix == source_table:
            return None, 0.0, ""

        # Direct match (e.g., customer -> customer)
        if prefix in table_names:
            return prefix, 0.95, "direct_match"

        # Plural match (e.g., customer -> customers)
        for plural_suffix in ['s', 'es', 'ies']:
            plural = prefix + plural_suffix
            if plural in table_names:
                return plural, 0.90, "plural_match"

        # Singular match (e.g., customers prefix -> customer table)
        # This handles cases like 'customers_id' -> 'customer' table
        for ending, replacement in self.PLURAL_ENDINGS.items():
            if prefix.endswith(ending):
                singular = prefix[:-len(ending)] + replacement
                if singular in table_names:
                    return singular, 0.85, "singular_match"

        # Underscore variations (e.g., user_account -> user_accounts)
        underscore_plural = prefix + 's'
        if underscore_plural in table_names:
            return underscore_plural, 0.80, "underscore_plural"

        # Common abbreviation expansions
        abbreviations = {
            'cust': 'customer',
            'prod': 'product',
            'emp': 'employee',
            'dept': 'department',
            'cat': 'category',
            'org': 'organization',
            'addr': 'address',
        }
        if prefix in abbreviations:
            expanded = abbreviations[prefix]
            if expanded in table_names:
                return expanded, 0.75, "abbreviation"
            # Try plural
            if expanded + 's' in table_names:
                return expanded + 's', 0.70, "abbreviation_plural"

        return None, 0.0, ""

    def compute_delta(
        self,
        old_dictionary: str,
        new_schema: SchemaInfo,
        connection_name: str
    ) -> Dict[str, Any]:
        """Compute delta between old dictionary and new schema.

        Args:
            old_dictionary: Existing dictionary Markdown content
            new_schema: New schema information
            connection_name: Connection name

        Returns:
            Delta information including added/removed tables/columns
        """
        # Parse old dictionary to extract existing tables/columns
        old_tables = self._parse_tables_from_markdown(old_dictionary)
        old_table_names = set(old_tables.keys())

        # Get new table names
        new_table_names = {t.name for t in new_schema.tables}

        # Compute differences
        added_tables = new_table_names - old_table_names
        removed_tables = old_table_names - new_table_names
        common_tables = old_table_names & new_table_names

        # Check for column changes in common tables
        added_columns: Dict[str, List[str]] = {}
        removed_columns: Dict[str, List[str]] = {}

        new_table_map = {t.name: t for t in new_schema.tables}

        for table_name in common_tables:
            old_cols = old_tables.get(table_name, set())
            new_cols = {c.name for c in new_table_map[table_name].columns}

            added = new_cols - old_cols
            removed = old_cols - new_cols

            if added:
                added_columns[table_name] = list(added)
            if removed:
                removed_columns[table_name] = list(removed)

        return {
            "added_tables": list(added_tables),
            "removed_tables": list(removed_tables),
            "added_columns": added_columns,
            "removed_columns": removed_columns,
            "has_changes": bool(added_tables or removed_tables or added_columns or removed_columns)
        }

    def _parse_tables_from_markdown(self, markdown: str) -> Dict[str, Set[str]]:
        """Parse table names and columns from existing dictionary Markdown.

        Args:
            markdown: Dictionary Markdown content

        Returns:
            Dict mapping table names to set of column names
        """
        tables: Dict[str, Set[str]] = {}
        current_table = None

        for line in markdown.split('\n'):
            # Match table headers like "### table_name" or "### table_name (~1,000 rows)"
            table_match = re.match(r'^###\s+(\w+)', line)
            if table_match:
                current_table = table_match.group(1)
                tables[current_table] = set()
                continue

            # Match column rows in table format "| column_name | type | ..."
            if current_table and line.startswith('|'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2 and parts[1] and not parts[1].startswith('-'):
                    # Skip header row
                    if parts[1].lower() != 'column':
                        tables[current_table].add(parts[1])

        return tables

    def merge_with_delta(
        self,
        old_dictionary: str,
        delta: Dict[str, Any],
        new_schema: SchemaInfo
    ) -> str:
        """Merge old dictionary with schema changes, preserving human edits.

        Args:
            old_dictionary: Existing dictionary content
            delta: Delta information from compute_delta
            new_schema: New schema information

        Returns:
            Merged dictionary preserving human descriptions
        """
        # For now, regenerate with preserved descriptions
        # TODO: Implement more sophisticated merging that preserves
        # human-added descriptions and notes

        if not delta["has_changes"]:
            return old_dictionary

        # Extract human descriptions from old dictionary
        descriptions = self._extract_descriptions(old_dictionary)

        # Generate new dictionary
        new_dict = self.generate_dictionary(
            new_schema,
            connection_name=self._extract_connection_name(old_dictionary),
            include_samples=True,
            include_inferred=True
        )

        # Apply preserved descriptions
        new_dict = self._apply_descriptions(new_dict, descriptions)

        return new_dict

    def _extract_descriptions(self, markdown: str) -> Dict[str, str]:
        """Extract human-added descriptions from dictionary.

        Args:
            markdown: Dictionary Markdown content

        Returns:
            Dict mapping "table.column" or "table" to descriptions
        """
        descriptions = {}
        current_table = None

        for line in markdown.split('\n'):
            # Match table headers
            table_match = re.match(r'^###\s+(\w+)', line)
            if table_match:
                current_table = table_match.group(1)
                continue

            # Match table descriptions
            desc_match = re.match(r'^\*\*Description\*\*:\s*(.+)$', line)
            if desc_match and current_table:
                desc = desc_match.group(1).strip()
                if not desc.startswith('[Add'):
                    descriptions[current_table] = desc
                continue

            # Match column descriptions in table rows
            if current_table and line.startswith('|'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5 and parts[1] and not parts[1].startswith('-'):
                    col_name = parts[1]
                    col_desc = parts[4] if len(parts) > 4 else ""
                    if col_desc and not col_desc.startswith('[Add'):
                        descriptions[f"{current_table}.{col_name}"] = col_desc

        return descriptions

    def _apply_descriptions(
        self,
        markdown: str,
        descriptions: Dict[str, str]
    ) -> str:
        """Apply preserved descriptions to new dictionary.

        Args:
            markdown: New dictionary Markdown
            descriptions: Preserved descriptions

        Returns:
            Markdown with descriptions applied
        """
        lines = markdown.split('\n')
        result = []
        current_table = None

        for line in lines:
            # Track current table
            table_match = re.match(r'^###\s+(\w+)', line)
            if table_match:
                current_table = table_match.group(1)
                result.append(line)
                continue

            # Replace table descriptions
            if current_table and line.startswith('**Description**:'):
                if current_table in descriptions:
                    result.append(f"**Description**: {descriptions[current_table]}")
                else:
                    result.append(line)
                continue

            # Replace column descriptions in table rows
            if current_table and line.startswith('|'):
                parts = line.split('|')
                if len(parts) >= 5:
                    col_name = parts[1].strip()
                    key = f"{current_table}.{col_name}"
                    if key in descriptions:
                        # Replace description (last column before final |)
                        parts[-2] = f" {descriptions[key]} "
                        result.append('|'.join(parts))
                        continue

            result.append(line)

        return '\n'.join(result)

    def _extract_connection_name(self, markdown: str) -> str:
        """Extract connection name from dictionary header.

        Args:
            markdown: Dictionary Markdown content

        Returns:
            Connection name or 'Unknown'
        """
        match = re.search(r'^#\s*Database Dictionary:\s*(.+)$', markdown, re.MULTILINE)
        return match.group(1).strip() if match else 'Unknown'
