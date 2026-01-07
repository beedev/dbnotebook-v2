"""
Data Masking for Chat with Data.

Applies column-level masking policies to query results.
Supports masking (****), redaction (remove), and hashing (anonymization).
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Set

from dbnotebook.core.sql_chat.types import MaskingPolicy

logger = logging.getLogger(__name__)


class DataMasker:
    """Apply column-level masking policy to query results.

    Supports three masking modes:
    - mask: Replace values with "****" (preserves column, hides data)
    - redact: Remove column entirely from results
    - hash: Replace with SHA-256 hash prefix (for analytics without exposure)
    """

    # Patterns for automatic sensitive data detection (for warnings)
    SENSITIVE_PATTERNS = {
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        "ssn": re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),
        "credit_card": re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    }

    # Column name patterns that often contain sensitive data
    SENSITIVE_COLUMN_PATTERNS = [
        r'(?i)(password|passwd|pwd|secret|token)',
        r'(?i)(ssn|social_security|social_sec)',
        r'(?i)(credit_card|cc_num|card_number)',
        r'(?i)(email|e_mail)',
        r'(?i)(phone|mobile|cell|telephone)',
        r'(?i)(address|addr|street)',
        r'(?i)(dob|date_of_birth|birth_date)',
        r'(?i)(salary|income|compensation)',
        r'(?i)(api_key|api_secret|access_token)',
    ]

    def __init__(self):
        """Initialize data masker."""
        self._sensitive_patterns = [
            re.compile(p) for p in self.SENSITIVE_COLUMN_PATTERNS
        ]

    def apply(
        self,
        results: List[Dict[str, Any]],
        policy: Optional[MaskingPolicy]
    ) -> List[Dict[str, Any]]:
        """Apply masking policy to query results.

        Args:
            results: Query result rows
            policy: Masking policy (mask, redact, hash columns)

        Returns:
            Masked results
        """
        if not policy:
            return results

        if not results:
            return results

        # Build column sets for efficient lookup (case-insensitive)
        mask_cols = {c.lower() for c in policy.mask_columns}
        redact_cols = {c.lower() for c in policy.redact_columns}
        hash_cols = {c.lower() for c in policy.hash_columns}

        masked_results = []
        for row in results:
            masked_row = {}
            for col, value in row.items():
                col_lower = col.lower()

                # Redact: skip column entirely
                if col_lower in redact_cols:
                    continue

                # Mask: replace with ****
                elif col_lower in mask_cols:
                    masked_row[col] = self._mask_value(value)

                # Hash: replace with hash prefix
                elif col_lower in hash_cols:
                    masked_row[col] = self._hash_value(value)

                # No masking
                else:
                    masked_row[col] = value

            masked_results.append(masked_row)

        return masked_results

    def _mask_value(self, value: Any) -> str:
        """Mask a value while preserving type hint.

        Args:
            value: Value to mask

        Returns:
            Masked value string
        """
        if value is None:
            return None

        str_val = str(value)

        # Detect and mask email format
        if '@' in str_val and '.' in str_val:
            return "****@****.***"

        # Detect and mask phone format
        if re.match(r'^\+?\d[\d\s-]{8,}$', str_val):
            return "***-***-****"

        # Generic masking
        return "****"

    def _hash_value(self, value: Any) -> str:
        """Hash a value for anonymized analytics.

        Args:
            value: Value to hash

        Returns:
            Hash prefix (12 chars) or None
        """
        if value is None:
            return None

        hash_input = str(value).encode()
        full_hash = hashlib.sha256(hash_input).hexdigest()
        return full_hash[:12]

    def detect_sensitive_columns(
        self,
        column_names: List[str]
    ) -> List[str]:
        """Detect potentially sensitive columns by name.

        Useful for warning users about columns that might need masking.

        Args:
            column_names: List of column names

        Returns:
            List of potentially sensitive column names
        """
        sensitive = []
        for col in column_names:
            for pattern in self._sensitive_patterns:
                if pattern.search(col):
                    sensitive.append(col)
                    break
        return sensitive

    def detect_sensitive_data(
        self,
        results: List[Dict[str, Any]],
        sample_size: int = 10
    ) -> Dict[str, Set[str]]:
        """Detect sensitive data patterns in result values.

        Args:
            results: Query results to scan
            sample_size: Number of rows to sample

        Returns:
            Dict mapping column names to detected sensitive data types
        """
        detected: Dict[str, Set[str]] = {}

        for row in results[:sample_size]:
            for col, value in row.items():
                if value is None:
                    continue

                str_val = str(value)
                for data_type, pattern in self.SENSITIVE_PATTERNS.items():
                    if pattern.search(str_val):
                        if col not in detected:
                            detected[col] = set()
                        detected[col].add(data_type)

        return detected

    def get_masking_summary(
        self,
        results: List[Dict[str, Any]],
        policy: Optional[MaskingPolicy]
    ) -> Dict[str, Any]:
        """Get summary of masking applied to results.

        Args:
            results: Query results
            policy: Applied policy

        Returns:
            Summary dict with counts and column lists
        """
        if not results:
            return {"rows": 0, "masked": [], "redacted": [], "hashed": []}

        all_columns = set()
        for row in results:
            all_columns.update(row.keys())

        masked = []
        redacted = []
        hashed = []

        if policy:
            mask_cols = {c.lower() for c in policy.mask_columns}
            redact_cols = {c.lower() for c in policy.redact_columns}
            hash_cols = {c.lower() for c in policy.hash_columns}

            for col in all_columns:
                col_lower = col.lower()
                if col_lower in mask_cols:
                    masked.append(col)
                elif col_lower in redact_cols:
                    redacted.append(col)
                elif col_lower in hash_cols:
                    hashed.append(col)

        return {
            "rows": len(results),
            "total_columns": len(all_columns),
            "masked_columns": masked,
            "redacted_columns": redacted,
            "hashed_columns": hashed,
        }

    def create_policy_from_detection(
        self,
        column_names: List[str],
        auto_detect: bool = True
    ) -> MaskingPolicy:
        """Create suggested masking policy based on column names.

        Args:
            column_names: List of column names
            auto_detect: Whether to auto-detect sensitive columns

        Returns:
            Suggested MaskingPolicy
        """
        mask_columns = []
        redact_columns = []
        hash_columns = []

        if auto_detect:
            for col in column_names:
                col_lower = col.lower()

                # Redact these (never expose)
                if any(x in col_lower for x in ['password', 'secret', 'token', 'api_key']):
                    redact_columns.append(col)

                # Mask these (show format, hide value)
                elif any(x in col_lower for x in ['email', 'phone', 'ssn', 'credit_card', 'address']):
                    mask_columns.append(col)

                # Hash these (for analytics)
                elif any(x in col_lower for x in ['user_id', 'customer_id', 'account_id']):
                    hash_columns.append(col)

        return MaskingPolicy(
            mask_columns=mask_columns,
            redact_columns=redact_columns,
            hash_columns=hash_columns,
        )
