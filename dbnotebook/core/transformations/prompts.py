"""Prompt templates for AI transformations.

These prompts are designed to generate high-quality transformations that:
1. Improve RAG retrieval by creating semantic-rich alternative representations
2. Provide users with quick document understanding
3. Support different query intents (overview, insights, exploration)
"""

DENSE_SUMMARY_PROMPT = """You are an expert document analyst. Create a comprehensive summary of the following document.

REQUIREMENTS:
- Length: 300-500 words
- Include: Main topics, key arguments, important findings, and conclusions
- Preserve: Technical terms, specific numbers, and named entities
- Structure: Use clear paragraphs with logical flow
- Tone: Professional and objective

DOCUMENT:
{text}

COMPREHENSIVE SUMMARY:"""


KEY_INSIGHTS_PROMPT = """You are an expert analyst. Extract the key insights and actionable takeaways from this document.

REQUIREMENTS:
- Extract 5-10 key insights
- Focus on practical, actionable points
- Include specific data points, recommendations, or conclusions
- Each insight should be self-contained and informative
- Prioritize insights by importance/impact

FORMAT: Return as a numbered list (1. insight, 2. insight, etc.)

DOCUMENT:
{text}

KEY INSIGHTS:"""


REFLECTION_QUESTIONS_PROMPT = """You are an expert educator. Generate thought-provoking questions that would help someone explore this document more deeply.

REQUIREMENTS:
- Generate 5-7 questions
- Questions should encourage critical thinking and application
- Include a mix of:
  - Comprehension questions (what/how)
  - Analysis questions (why/what if)
  - Application questions (how would you use this)
- Questions should be answerable from the document content

FORMAT: Return as a numbered list (1. question?, 2. question?, etc.)

DOCUMENT:
{text}

REFLECTION QUESTIONS:"""


# Shorter versions for very long documents (chunked processing)
DENSE_SUMMARY_CHUNK_PROMPT = """Summarize this document section, focusing on key points and findings.
Keep the summary under 200 words but capture all important information.

SECTION:
{text}

SUMMARY:"""


# Prompt for combining chunk summaries
COMBINE_SUMMARIES_PROMPT = """You are given summaries of different sections of a document.
Combine them into a single comprehensive summary (300-500 words).

REQUIREMENTS:
- Maintain coherent narrative flow
- Eliminate redundancy
- Preserve all key information
- Use professional, objective tone

SECTION SUMMARIES:
{summaries}

COMBINED SUMMARY:"""
