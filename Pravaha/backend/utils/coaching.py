"""
Real-time sales coaching engine.
Receives live call transcript chunks via VAPI webhook,
detects objections/signals with LLM, and pushes coaching tips via WebSocket.
"""
import json
import logging
import os
import re
from langchain_groq.chat_models import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))

COACHING_PROMPT = ChatPromptTemplate.from_template("""
You are an expert real-time sales coach. A sales rep is on a live call.

Latest customer utterance: "{utterance}"

Analyze if this contains:
1. A price/budget objection → type: "objection", subtype: "price"
2. A competitor mention → type: "objection", subtype: "competitor"
3. A timeline concern → type: "objection", subtype: "timing"
4. A feature/product question → type: "question"
5. A buying signal (interest, urgency, positive reaction) → type: "signal"
6. A request for more information → type: "info_request"
7. Nothing significant → type: "none"

If something significant is detected, respond with ONLY valid JSON (no markdown, no extra text):
{{
  "type": "objection|question|signal|info_request|none",
  "subtype": "price|competitor|timing|feature|general",
  "detected": "one sentence describing what you detected",
  "suggested_response": "what the rep should say next (max 2 sentences)",
  "urgency": "high|medium|low"
}}

If nothing significant, respond with exactly: {{"type": "none"}}
""")

coaching_chain = LLMChain(llm=llm, prompt=COACHING_PROMPT)


def analyze_utterance(utterance: str) -> dict:
    """
    Analyze a single customer utterance and return a coaching tip dict.
    Returns {"type": "none"} if nothing significant is detected.
    """
    if not utterance or len(utterance.strip()) < 10:
        return {"type": "none"}

    try:
        result = coaching_chain.invoke({"utterance": utterance})
        result = result.get("text", str(result)) if isinstance(result, dict) else str(result)
        result = result.strip()
        # Extract JSON object regardless of surrounding markdown or text
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if not match:
            return {"type": "none"}
        tip = json.loads(match.group())
        return tip
    except Exception as e:
        logger.exception("coaching: LLM parse error for utterance '%.80s'", utterance)
        return {"type": "none"}
