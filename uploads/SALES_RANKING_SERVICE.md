# SalesRankingService Integration

## Overview

Integrated `SalesRankingService` to enrich search results with `BOUGHT_TOGETHER` purchase intelligence from Neo4j.

- **Date**: December 1, 2025
- **Status**: COMPLETED (for proactive searches)
- **Purpose**: Surface products frequently purchased together based on historical sales data

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Search Flow with Sales Intelligence              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User selects PowerSource → Navigate to Feeder selection               │
│      │                                                                  │
│      ├─ ComponentSearchService.search()                                │
│      │      │                                                          │
│      │      ├─ Execute Cypher query → Get compatible products          │
│      │      │                                                          │
│      │      ├─ SalesRankingService.enrich_with_sales_intelligence()   │
│      │      │      │                                                   │
│      │      │      ├─ Query Neo4j BOUGHT_TOGETHER relationships       │
│      │      │      ├─ Enrich with intelligence_score                  │
│      │      │      ├─ Add name suffix "[Bought Together: Nx]"         │
│      │      │      └─ Re-sort by intelligence_score DESC              │
│      │      │                                                          │
│      │      └─ Return enriched, sorted results                        │
│      │                                                                  │
│      └─ Display to user                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Files Modified

| File | Location | Changes |
|------|----------|---------|
| `product_search.py` | `app/models/` | Added 3 sales intelligence fields to ProductResult |
| `component_service.py` | `app/services/search/components/` | Added import, init, enrichment call, helper method |
| `sales_ranking.py` | `app/services/search/` | Already existed (was dead code, now active) |

---

## Code Changes

### 1. ProductResult Model

**File**: `app/models/product_search.py`

Added sales intelligence fields to the ProductResult model:

```python
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class ProductResult(BaseModel):
    """Single product search result"""
    gin: str
    name: str
    category: str
    description: Optional[str] = None
    specifications: Dict[str, Any] = {}
    priority: Optional[int] = None  # Priority from COMPATIBLE_WITH relationship

    # ========== NEW: Sales intelligence fields ==========
    # Populated by SalesRankingService after search
    intelligence_score: float = 0.0           # Score from BOUGHT_TOGETHER relationships
    bought_together_frequency: int = 0        # How many times bought with parent component
    is_top_recommendation: bool = False       # Flag for top 3 recommended products
```

---

### 2. ComponentSearchService Integration

**File**: `app/services/search/components/component_service.py`

#### 2.1 Import Statement (Line 32)

```python
from app.services.search.sales_ranking import SalesRankingService
```

#### 2.2 Service Initialization (Lines 72-73)

In `__init__` method:

```python
def __init__(self, driver: AsyncDriver, llm_service: LLMService):
    self.driver = driver
    self.llm_service = llm_service
    self.logger = logging.getLogger(__name__)

    # Initialize sales ranking service for BOUGHT_TOGETHER intelligence
    self.sales_ranking = SalesRankingService(self.driver)
```

#### 2.3 Enrichment Call in search() Method (Lines 246-254)

Added after Cypher query results, before returning:

```python
async def search(
    self,
    component_type: str,
    user_intent: str,
    selected_components: Dict[str, Any],
    ...
) -> SearchResults:
    # ... existing search logic ...

    # ========== NEW: ENRICH WITH SALES INTELLIGENCE ==========
    # Get selected parent GIN for BOUGHT_TOGETHER lookup
    selected_parent_gin = self._get_selected_parent_gin(component_type, selected_components)
    if selected_parent_gin:
        products = await self.sales_ranking.enrich_with_sales_intelligence(
            products=products,
            selected_component_gin=selected_parent_gin,
            component_type=component_type
        )

    return SearchResults(
        products=products,
        total_count=len(products),
        ...
    )
```

#### 2.4 Helper Method (Lines 587-636)

```python
def _get_selected_parent_gin(
    self,
    component_type: str,
    selected_components: Dict[str, Any]
) -> Optional[str]:
    """
    Extract the selected parent component GIN for BOUGHT_TOGETHER intelligence.

    Maps component types to their parent dependencies:
    - feeder → PowerSource
    - cooler → PowerSource
    - torch → Feeder (or PowerSource if no Feeder)
    - interconnector → PowerSource

    Args:
        component_type: Type of component being searched
        selected_components: ResponseJSON dict with selected components

    Returns:
        GIN of selected parent component, or None if no parent selected
    """
    # Map component types to their parent components
    parent_map = {
        "feeder": "PowerSource",
        "cooler": "PowerSource",
        "torch": "Feeder",  # Torches bought with feeders
        "interconnector": "PowerSource"
    }

    parent_key = parent_map.get(component_type)
    if not parent_key:
        return None

    # Extract parent component
    parent = None
    if hasattr(selected_components, parent_key):
        parent = getattr(selected_components, parent_key)
    elif isinstance(selected_components, dict):
        parent = selected_components.get(parent_key)

    if not parent:
        return None

    # Extract GIN from parent
    if isinstance(parent, dict):
        return parent.get("gin")
    elif hasattr(parent, "gin"):
        return parent.gin

    return None
```

---

### 3. SalesRankingService (Complete Implementation)

**File**: `app/services/search/sales_ranking.py`

```python
"""
Sales Ranking Enrichment Service

Post-processes search results with BOUGHT_TOGETHER intelligence from Neo4j.
Enriches ProductResult objects with purchase affinity data without modifying
the core search query logic.

Architecture:
- Takes existing search results from ComponentSearchService
- Queries Neo4j for BOUGHT_TOGETHER relationships
- Enriches ProductResult objects with intelligence_score, bought_together_frequency
- Re-sorts results: intelligence_score DESC, then original order
- Marks top 3 as recommendations
"""

import logging
from typing import List, Optional, Dict, Any
from neo4j import AsyncDriver

from app.models.product_search import ProductResult

logger = logging.getLogger(__name__)


class SalesRankingService:
    """
    Enriches search results with sales ranking intelligence from BOUGHT_TOGETHER relationships.

    This service is called AFTER standard search to add purchase affinity data
    without modifying the core search queries.
    """

    def __init__(self, driver: AsyncDriver):
        """
        Initialize sales ranking service.

        Args:
            driver: Neo4j async driver instance
        """
        self.driver = driver
        logger.info("SalesRankingService initialized")

    async def enrich_with_sales_intelligence(
        self,
        products: List[ProductResult],
        selected_component_gin: Optional[str] = None,
        component_type: Optional[str] = None
    ) -> List[ProductResult]:
        """
        Enrich product results with BOUGHT_TOGETHER intelligence.

        Flow:
        1. Query Neo4j for BOUGHT_TOGETHER relationships
        2. Create intelligence score map (gin -> score)
        3. Enrich ProductResult objects with intelligence fields
        4. Re-sort: Products with intelligence data first (by score DESC), then others
        5. Mark top 3 as recommendations

        Args:
            products: List of ProductResult from standard search
            selected_component_gin: GIN of selected parent component (e.g., PowerSource GIN)
            component_type: Type of component being searched (for logging)

        Returns:
            Enriched and re-sorted product list
        """
        if not products:
            return products

        if not selected_component_gin:
            logger.debug(f"No selected component GIN provided - skipping sales intelligence")
            return products

        # Query BOUGHT_TOGETHER relationships
        intelligence_map = await self._query_bought_together_intelligence(
            selected_component_gin=selected_component_gin,
            product_gins=[p.gin for p in products],
            component_type=component_type
        )

        if not intelligence_map:
            logger.debug(f"No BOUGHT_TOGETHER data found for {selected_component_gin}")
            return products

        # Enrich products with intelligence data
        enriched_products = []
        for product in products:
            intelligence_data = intelligence_map.get(product.gin, {})
            intelligence_score = intelligence_data.get("score", 0.0)
            bought_together_freq = intelligence_data.get("frequency", 0)

            # Add sales intelligence to product name if data exists
            product_name = product.name
            if intelligence_score > 0:
                product_name = f"{product.name} [Bought Together: {bought_together_freq}x, Score: {intelligence_score:.1f}]"

            # Create enriched copy
            enriched = ProductResult(
                gin=product.gin,
                name=product_name,
                category=product.category,
                description=product.description,
                specifications=product.specifications,
                priority=product.priority,
                intelligence_score=intelligence_score,
                bought_together_frequency=bought_together_freq,
                is_top_recommendation=False
            )
            enriched_products.append(enriched)

        # Sort: Products with intelligence data first (by score DESC)
        products_with_intelligence = [p for p in enriched_products if p.intelligence_score > 0]
        products_without_intelligence = [p for p in enriched_products if p.intelligence_score == 0]

        products_with_intelligence.sort(
            key=lambda p: (p.intelligence_score, p.bought_together_frequency),
            reverse=True
        )

        sorted_products = products_with_intelligence + products_without_intelligence

        # Mark top 3 as recommendations
        for idx, product in enumerate(sorted_products[:3]):
            product.is_top_recommendation = True

        logger.info(
            f"Sales intelligence enrichment: {len(products_with_intelligence)} products with data, "
            f"{len(products_without_intelligence)} without data"
        )

        return sorted_products

    async def _query_bought_together_intelligence(
        self,
        selected_component_gin: str,
        product_gins: List[str],
        component_type: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Query Neo4j for BOUGHT_TOGETHER relationships.

        Returns map of {product_gin: {"score": float, "frequency": int}}
        """
        query = """
        MATCH (parent {gin: $parent_gin})
        MATCH (product)
        WHERE product.gin IN $product_gins
        OPTIONAL MATCH (parent)-[bt:BOUGHT_TOGETHER]->(product)
        RETURN product.gin as gin,
               COALESCE(bt.frequency, 0) as frequency,
               COALESCE(bt.frequency, 0) as score
        """

        params = {
            "parent_gin": selected_component_gin,
            "product_gins": product_gins
        }

        try:
            async with self.driver.session() as session:
                result = await session.run(query, params)
                records = await result.data()

                intelligence_map = {}
                for record in records:
                    gin = record["gin"]
                    frequency = record["frequency"]
                    score = record["score"]

                    if frequency > 0:
                        intelligence_map[gin] = {
                            "frequency": frequency,
                            "score": float(score)
                        }

                logger.info(
                    f"Found BOUGHT_TOGETHER data for {len(intelligence_map)}/{len(product_gins)} products "
                    f"(parent: {selected_component_gin}, type: {component_type})"
                )

                return intelligence_map

        except Exception as e:
            logger.error(f"Error querying BOUGHT_TOGETHER intelligence: {e}", exc_info=True)
            return {}
```

---

## Neo4j Data Model

### BOUGHT_TOGETHER Relationship

```
(PowerSource)-[:BOUGHT_TOGETHER {frequency: 127}]->(Feeder)
(PowerSource)-[:BOUGHT_TOGETHER {frequency: 89}]->(Cooler)
(Feeder)-[:BOUGHT_TOGETHER {frequency: 45}]->(Torch)
```

### Cypher Query

```cypher
MATCH (parent {gin: $parent_gin})
MATCH (product)
WHERE product.gin IN $product_gins
OPTIONAL MATCH (parent)-[bt:BOUGHT_TOGETHER]->(product)
RETURN product.gin as gin,
       COALESCE(bt.frequency, 0) as frequency,
       COALESCE(bt.frequency, 0) as score
```

---

## Current Coverage

| Search Type | Strategy | SalesRanking Applied? | Notes |
|-------------|----------|----------------------|-------|
| Proactive (empty/skip/next) | Cypher | YES | Enriched after Cypher results |
| User Intent (text query) | LLM | NO | Uses LLM relevance scores |

---

## Verification

### Backend Logs

When SalesRankingService is active, you'll see:

```
INFO: SalesRankingService initialized
INFO: Found BOUGHT_TOGETHER data for 3/10 products (parent: 0446200880, type: feeder)
INFO: Sales intelligence enrichment: 3 products with data, 7 without data
```

### Product Display

Products with purchase history show:
- `[Bought Together: 3x, Score: 3.0]` suffix in product names
- Sorted by `intelligence_score` DESC (products with data first)
- Top 3 marked with `is_top_recommendation = True`

---

## Future Enhancements (Not Implemented)

1. **LLM Strategy Integration**: Apply sales ranking to user intent searches
2. **Weighted Scoring**: Combine BOUGHT_TOGETHER with other signals (reviews, margin)
3. **Time Decay**: Weight recent purchases higher than older ones
4. **Cross-Category**: Track purchases across component categories
