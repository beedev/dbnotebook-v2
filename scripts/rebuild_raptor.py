#!/usr/bin/env python3
"""
Rebuild RAPTOR trees for a notebook.

This script:
1. Deletes existing RAPTOR summaries (tree_level >= 1)
2. Resets raptor_status to 'pending' for all sources
3. The background worker will then rebuild with updated prompts

Usage:
    python scripts/rebuild_raptor.py --notebook-id <uuid>
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def get_database_url():
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('POSTGRES_USER', 'dbnotebook')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'dbnotebook')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5433')}/"
        f"{os.getenv('POSTGRES_DB', 'dbnotebook_dev')}"
    )


def rebuild_raptor(notebook_id: str, verbose: bool = False):
    """Delete RAPTOR summaries and reset status for rebuild."""

    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Get all source IDs for this notebook
        result = session.execute(
            text("""
                SELECT source_id, file_name
                FROM notebook_sources
                WHERE notebook_id = :notebook_id
            """),
            {"notebook_id": notebook_id}
        )
        sources = result.fetchall()

        if not sources:
            print(f"No sources found for notebook {notebook_id}")
            return

        print(f"Found {len(sources)} sources in notebook")

        total_deleted = 0

        for source_id, file_name in sources:
            # 2. Delete RAPTOR summaries (tree_level >= 1)
            result = session.execute(
                text("""
                    DELETE FROM data_embeddings
                    WHERE metadata_->>'source_id' = :source_id
                    AND (metadata_->>'tree_level')::int >= 1
                """),
                {"source_id": str(source_id)}
            )
            deleted = result.rowcount
            total_deleted += deleted

            if verbose:
                print(f"  Deleted {deleted} RAPTOR nodes for: {file_name}")

        # 3. Reset raptor_status to 'pending' for all sources
        result = session.execute(
            text("""
                UPDATE notebook_sources
                SET raptor_status = 'pending', raptor_error = NULL
                WHERE notebook_id = :notebook_id
            """),
            {"notebook_id": notebook_id}
        )
        updated = result.rowcount

        session.commit()

        print(f"\nTotal RAPTOR nodes deleted: {total_deleted}")
        print(f"Sources reset to pending: {updated}")
        print("\nRAPTOR trees will be rebuilt by the background worker.")
        print("Monitor logs for: 'Building RAPTOR tree for source'")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Rebuild RAPTOR trees for a notebook")
    parser.add_argument("--notebook-id", required=True, help="Notebook UUID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    rebuild_raptor(args.notebook_id, args.verbose)


if __name__ == "__main__":
    main()
