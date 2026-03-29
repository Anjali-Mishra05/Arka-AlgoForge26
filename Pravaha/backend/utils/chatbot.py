import os
from datetime import datetime
from typing import Any, Dict, Optional

import dotenv
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from utils.database import Database

dotenv.load_dotenv()

# Role-based system prompt templates - FIRST MESSAGE
ROLE_PROMPTS_FIRST = {
    "user": """Hello again. I'm Pravaha, your product assistant. How can I help you?""",
    "team": """Hello! I'm Pravaha, your sales coach. What objection or question do we need to tackle?""",
    "admin": """Hello! I'm Pravaha, your sales intelligence expert. What insights do you need?""",
}

# Role-based system prompt templates - FOLLOW UP MESSAGES
ROLE_PROMPTS_FOLLOW_UP = {
    "user": """You are a helpful product assistant. Follow this simple universal flow:

STEP 1: If customer hasn't clearly stated their needs → Ask about their specific needs/requirements
STEP 2: After you understand their needs, if budget isn't clear → Ask about budget
STEP 3: After you know both needs AND budget → Give specific recommendations based on their request

Rules:
- Be natural and casual, no fluff
- Only ask essential questions (needs, then budget) - nothing else
- Adapt to ANY product/service they ask about, not just one category
- After getting both pieces of info, recommend specific options
- Keep each response to 1-2 sentences max
- Stay focused on what THEY want, not assumptions

Company context:
{company_context}

Email insights:
{email_insights}

Previous conversation:
{chat_history}

Customer message: {text}

Your response:""",

    "team": """You are pravaha, a real-time sales coach for the sales representative.
Your goal is to help the rep handle objections, pitch effectively, and close the deal.
Be concise - max 2 sentences. The rep is likely on a live call so brevity is critical.
Detect the type of message and respond appropriately.

Company context:
{company_context}

Previous conversation:
{chat_history}

Message: {text}

Your response:""",

    "admin": """You are pravaha, an intelligent sales intelligence assistant for the sales manager.
Your goal is to surface insights, flag risks, and summarize deal health.
Be analytical and structured. Use bullet points when listing multiple items.

Company context:
{company_context}

Previous conversation:
{chat_history}

Question: {text}

Your response:""",
}


class ChatBot:
    def __init__(self, temperature=0, model_name="llama-3.1-8b-instant", role="user"):
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        self.chat = ChatGroq(temperature=temperature, model_name=model_name, api_key=groq_api_key)
        self.role = role
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="text",
            return_messages=True,
            max_token_limit=250,
        )
        self.db = Database("pravaha_app")

    def _get_email_insights_context(self) -> str:
        """Fetch recent email campaign themes for cross-channel personalization."""
        try:
            insights = self.db.get_email_insights(limit=10)
            themes = insights.get("themes", [])
            subjects = insights.get("top_subjects", [])
            if not themes and not subjects:
                return ""
            parts = []
            if themes:
                parts.append("Themes: " + ", ".join(t["theme"] for t in themes[:2]))
            if subjects:
                parts.append("Subjects: " + "; ".join(subjects[:3]))
            return "\n".join(parts)
        except Exception:
            return ""

    def _get_company_context(self, user_id: Optional[str] = None) -> str:
        """Fetch company profile for personalization."""
        if not user_id:
            return ""
        try:
            onboarding = self.db.get_onboarding(user_id) or {}
            parts = []
            if onboarding.get("company_name"):
                parts.append(f"Company: {onboarding['company_name']}")
            if onboarding.get("industry"):
                parts.append(f"Industry: {onboarding['industry']}")
            return " | ".join(parts) if parts else ""
        except Exception:
            return ""

    def invoke(
        self,
        text: str,
        document_data: str = "",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        proposal_context: Optional[str] = None,
        include_all_proposals: bool = True,
        persist_session: bool = True,
    ):
        # Check if this is the first message
        is_first_message = len(self.memory.buffer_as_messages) == 0
        
        # For first message, return greeting
        if is_first_message:
            greeting = ROLE_PROMPTS_FIRST.get(self.role, ROLE_PROMPTS_FIRST["user"])
            self.memory.save_context({"text": text}, {"text": greeting})
            if persist_session:
                self.append_session(
                    {
                        "user": "AI",
                        "message": greeting,
                        "role": self.role,
                        "created_at": datetime.utcnow(),
                    },
                    user_id=user_id,
                    session_id=session_id,
                )
            return greeting

        # For follow-up messages, generate response
        proposal_str = ""
        if proposal_context is not None:
            proposal_str = proposal_context
        elif include_all_proposals:
            proposal = self.get_proposal()
            proposal_str = " ".join(proposal) if isinstance(proposal, list) else proposal
        
        limited_doc_data = document_data[:50] if document_data else ""
        combined_context = text[:200]
        if limited_doc_data:
            combined_context += f"\nDocs: {limited_doc_data}"
        if proposal_str:
            combined_context += f"\nProposal: {proposal_str[:50]}"

        template = ROLE_PROMPTS_FOLLOW_UP.get(self.role, ROLE_PROMPTS_FOLLOW_UP["user"])
        prompt = ChatPromptTemplate.from_template(template=template)
        chain = LLMChain(llm=self.chat, prompt=prompt, memory=self.memory)

        email_ctx = self._get_email_insights_context()
        company_ctx = self._get_company_context(user_id)

        inputs = {
            "text": combined_context,
            "email_insights": email_ctx[:50],
            "company_context": company_ctx[:50],
        }
        
        ai_response = chain.invoke(inputs)
        ai_text = ai_response["text"]
        
        if persist_session:
            self.append_session(
                {
                    "user": "AI",
                    "message": ai_text,
                    "role": self.role,
                    "created_at": datetime.utcnow(),
                },
                user_id=user_id,
                session_id=session_id,
            )
        return ai_text

    def get_sessions_by_user_id(self, user_id, limit=10):
        return self.db.get_sessions_by_user_id(user_id, limit)

    def get_proposal(self):
        proposals = self.db.get_all_proposals()
        proposal_texts = []
        for p in proposals:
            if 'proposal' in p:
                proposal_texts.append(p['proposal'])
            elif 'markdown_content' in p:
                proposal_texts.append(p['markdown_content'])
            elif 'html_content' in p:
                proposal_texts.append(p['html_content'])
        return proposal_texts

    def append_session(
        self,
        session: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        payload = dict(session)
        if user_id:
            payload["user_id"] = user_id
        if session_id:
            payload["session_id"] = session_id
        payload.setdefault("role", self.role)
        self.db.append_session(payload)


def main():
    dotenv.load_dotenv()
    os.getenv("CONNECTION_STRING")
    bot = ChatBot()
    response2 = bot.invoke("I want to buy a new laptop")
    print("Bot response 2:", response2)
    response3 = bot.invoke("I am going to use it for video editing. So i would need a beast.")
    print("Bot response 3:", response3)
    response4 = bot.invoke("What is the cost?")
    print("Bot response 4:", response4)


if __name__ == "__main__":
    main()
