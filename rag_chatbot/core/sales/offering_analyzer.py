"""Offering analysis and recommendation for problem-solving queries."""
import logging
from typing import Dict, List, Optional
from llama_index.core.schema import BaseNode, QueryBundle
from llama_index.core.llms.llm import LLM

logger = logging.getLogger(__name__)


class OfferingAnalyzer:
    """
    Analyzes customer problems and recommends offering bundles.

    Core functionality:
    1. Query each offering with the problem description
    2. Score relevance of each offering to the problem
    3. Recommend top N offerings as a bundle
    4. Generate explanation of how each offering solves the problem
    """

    def __init__(self, llm: LLM):
        """
        Initialize offering analyzer.

        Args:
            llm: Language model for scoring and explanation generation
        """
        self._llm = llm
        logger.debug("OfferingAnalyzer initialized")

    def analyze_problem(
        self,
        problem_description: str,
        offering_synopses: Dict[str, str],
        customer_name: Optional[str] = None,
        industry: Optional[str] = None,
        top_n: int = 3,
        min_score_threshold: float = 0.70
    ) -> Dict:
        """
        Analyze a customer problem and recommend offering bundle based on relevance scores.

        Uses pre-generated synopses for faster analysis.

        Args:
            problem_description: Description of customer's problem
            offering_synopses: Dict of {offering_name: synopsis_text} (pre-generated)
            customer_name: Optional customer name
            industry: Optional industry
            top_n: Maximum number of offerings to recommend
            min_score_threshold: Minimum score (0.0-1.0) for an offering to be recommended (default: 0.70)

        Returns:
            Dictionary with:
            {
                "recommended_offerings": List[str],  # Offerings above threshold, sorted by score
                "offering_scores": Dict[str, float],  # Offering -> relevance score
                "offering_explanations": Dict[str, str],  # Offering -> explanation
                "bundle_strategy": str  # Overall bundle recommendation
            }
        """
        logger.info(f"Analyzing problem: {problem_description[:100]}...")
        logger.info(f"Using pre-generated synopses for {len(offering_synopses)} offerings")

        # Score each offering against the problem using pre-generated synopses
        logger.info("Scoring offerings against problem statement...")
        offering_scores = {}
        offering_explanations = {}

        for offering_name, synopsis in offering_synopses.items():
            logger.debug(f"Scoring offering: {offering_name}")

            # Score offering based on synopsis vs problem
            score, explanation = self._score_offering_with_synopsis(
                offering_name=offering_name,
                synopsis=synopsis,
                problem_description=problem_description,
                customer_name=customer_name,
                industry=industry
            )

            offering_scores[offering_name] = score
            offering_explanations[offering_name] = explanation

        # Filter offerings by minimum score threshold, then sort by score
        qualified_offerings = [
            (name, score) for name, score in offering_scores.items()
            if score >= min_score_threshold
        ]

        # Sort qualified offerings by score and limit to top_n
        sorted_offerings = sorted(
            qualified_offerings,
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        recommended_offerings = [name for name, score in sorted_offerings]

        # Log recommendation details
        logger.info(f"Qualified offerings (score >= {min_score_threshold}): {len(qualified_offerings)}")
        for name, score in sorted_offerings:
            logger.info(f"  - {name}: {score:.2f}")

        if not recommended_offerings:
            logger.warning(f"No offerings met minimum threshold of {min_score_threshold}")
            # Fallback: recommend best offering even if below threshold
            if offering_scores:
                best_offering = max(offering_scores.items(), key=lambda x: x[1])
                recommended_offerings = [best_offering[0]]
                logger.info(f"Fallback: recommending best available offering: {best_offering[0]} (score: {best_offering[1]:.2f})")

        # Generate bundle strategy
        bundle_strategy = self._generate_bundle_strategy(
            recommended_offerings=recommended_offerings,
            offering_explanations=offering_explanations,
            problem_description=problem_description
        )

        return {
            "recommended_offerings": recommended_offerings,
            "offering_scores": offering_scores,
            "offering_explanations": offering_explanations,
            "bundle_strategy": bundle_strategy
        }

    def _score_offering_with_synopsis(
        self,
        offering_name: str,
        synopsis: str,
        problem_description: str,
        customer_name: Optional[str],
        industry: Optional[str]
    ) -> tuple[float, str]:
        """
        Score an offering's relevance to a problem based on its synopsis.

        This method compares the offering synopsis against the customer's problem
        to determine how well it addresses the specific pain points.

        Args:
            offering_name: Name of the offering
            synopsis: Comprehensive synopsis of the offering
            problem_description: Customer's problem statement
            customer_name: Optional customer name
            industry: Optional industry context

        Returns:
            (score, explanation) tuple where:
            - score: 0.0-1.0 relevance score
            - explanation: Detailed analysis of how offering solves the problem
        """
        scoring_prompt = f"""You are a solutions architect analyzing how well a technology offering solves a specific customer problem.

Customer Context:
- Problem: {problem_description}
{f'- Customer: {customer_name}' if customer_name else ''}
{f'- Industry: {industry}' if industry else ''}

Offering to Analyze: {offering_name}

Offering Synopsis:
{synopsis}

Your Task:
1. **Analyze the Problem**: Break down the specific pain points, challenges, and requirements in the customer's problem
2. **Match Capabilities**: Identify which aspects of {offering_name} directly address these pain points
3. **Assess Fit**: Determine if this offering solves the FULL problem, PART of the problem, or is NOT RELEVANT
4. **Consider Context**: Factor in the industry context and any specific customer requirements

Scoring Guidelines:
- 0.9-1.0: Excellent fit - Solves the complete problem comprehensively
- 0.7-0.89: Strong fit - Solves most of the problem or critical parts
- 0.5-0.69: Moderate fit - Solves part of the problem, may need complementary solutions
- 0.3-0.49: Weak fit - Addresses only tangential aspects
- 0.0-0.29: Poor fit - Not relevant to the problem

Provide:
- SCORE: A number between 0.0 and 1.0 based on the guidelines above
- EXPLANATION: A consultative analysis (4-6 sentences) that:
  * Identifies which specific pain points this offering addresses
  * Explains the value proposition in the customer's context
  * Describes whether it solves FULL or PARTIAL aspects of the problem
  * Mentions any gaps, limitations, or complementary needs
  * Uses creative, business-value focused language

Format your response as:
SCORE: <number>
EXPLANATION: <your analysis>
"""

        try:
            response = self._llm.complete(scoring_prompt)
            response_text = response.text

            # Parse score and explanation
            score = 0.5  # default
            explanation = ""

            if "SCORE:" in response_text:
                score_line = response_text.split("SCORE:")[1].split("\n")[0]
                try:
                    score = float(score_line.strip())
                    # Clamp score to valid range
                    score = max(0.0, min(1.0, score))
                except:
                    logger.warning(f"Could not parse score for {offering_name}, using default 0.5")
                    pass

            if "EXPLANATION:" in response_text:
                explanation = response_text.split("EXPLANATION:")[1].strip()

            logger.debug(f"Scored {offering_name}: {score:.2f}")
            return score, explanation

        except Exception as e:
            logger.error(f"Error scoring offering {offering_name}: {e}")
            return 0.0, "Unable to analyze this offering."

    def _generate_bundle_strategy(
        self,
        recommended_offerings: List[str],
        offering_explanations: Dict[str, str],
        problem_description: str
    ) -> str:
        """Generate creative, strategic bundle explanation."""
        if not recommended_offerings:
            return "No suitable offerings found for this problem."

        bundle_prompt = f"""You are a strategic solutions consultant designing a technology bundle for a customer.

Customer's Problem:
{problem_description}

Recommended Solution Bundle:
{chr(10).join([f"- {name}: {offering_explanations.get(name, '')}" for name in recommended_offerings])}

Your Task:
Create a compelling, strategic narrative (4-6 sentences) that:
1. Explains how these offerings work TOGETHER synergistically (not just separately)
2. Describes the customer journey from current pain points to desired outcomes
3. Highlights the unique value of combining these specific offerings
4. Uses consultative, business-value focused language (not just technical features)
5. Mentions potential quick wins and long-term strategic benefits

Think like a trusted advisor presenting a transformation roadmap, not just a product bundle.

Your Strategic Bundle Narrative:
"""

        try:
            response = self._llm.complete(bundle_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating bundle strategy: {e}")
            return f"Recommended bundle: {', '.join(recommended_offerings)}"

    def generate_implementation_plan(
        self,
        recommended_offerings: List[str],
        offering_synopses: Dict[str, str],
        problem_description: str,
        customer_name: Optional[str] = None,
        industry: Optional[str] = None
    ) -> str:
        """
        Generate a high-level implementation plan based on recommended offerings.

        This creates a structured roadmap showing how to implement the offerings
        to solve the customer's problem, including phases, milestones, and dependencies.

        Args:
            recommended_offerings: List of recommended offering names
            offering_synopses: Full synopses of offerings
            problem_description: Customer's problem statement
            customer_name: Optional customer name
            industry: Optional industry context

        Returns:
            High-level implementation plan as formatted text
        """
        if not recommended_offerings:
            return "No offerings to plan implementation for."

        # Build offering context from synopses
        offering_details = "\n\n".join([
            f"**{name}**:\n{offering_synopses.get(name, 'Synopsis not available')}"
            for name in recommended_offerings
        ])

        plan_prompt = f"""You are a senior solutions architect creating a high-level implementation plan for a customer.

Customer Context:
- Problem: {problem_description}
{f'- Customer: {customer_name}' if customer_name else ''}
{f'- Industry: {industry}' if industry else ''}

Recommended Solution Offerings:
{offering_details}

Your Task:
Create a high-level implementation plan (300-400 words) that outlines:

1. **Implementation Phases** (3-4 phases):
   - Phase 1: Foundation & Quick Wins
   - Phase 2: Core Implementation
   - Phase 3: Integration & Optimization
   - Phase 4: Scaling & Continuous Improvement (if applicable)

2. **Key Milestones**: What does success look like at each phase?

3. **Dependencies**: Which offerings need to be implemented first? What are the technical dependencies?

4. **Risk Mitigation**: What are potential challenges and how to address them?

5. **Timeline Estimate**: Rough timeline for each phase (weeks/months)

Focus on:
- Practical, actionable steps
- Business value delivery at each phase
- Risk awareness and mitigation
- Clear sequencing based on dependencies

Write in a professional, consultative tone suitable for presenting to stakeholders.

Implementation Plan:"""

        try:
            response = self._llm.complete(plan_prompt)
            plan = response.text.strip()
            logger.debug(f"Generated implementation plan: {len(plan)} chars")
            return plan
        except Exception as e:
            logger.error(f"Error generating implementation plan: {e}")
            return f"Implementation plan for: {', '.join(recommended_offerings)}"
