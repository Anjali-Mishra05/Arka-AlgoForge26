import os
import dotenv
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain.globals import set_llm_cache
from langchain_community.cache import InMemoryCache
import pypandoc

set_llm_cache(InMemoryCache())
from langchain.chains import LLMChain
from utils.markdown_to_html import markdown_to_html_file
from utils.database import APP_DB_NAME, Database
from utils.hubspot import sync_proposal_generation_to_crm

dotenv.load_dotenv()
from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import PyPDFLoader, PyPDFDirectoryLoader

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
chat = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant")


def generate_proposal(created_by: str = "admin", documents_used: list = None):
    files = os.listdir("./input_documents")
    if len(files) == 0:
        print("No files found in input_documents folder.")
        return {"message": "No files found in input_documents folder."}

    # Get the user's texts
    texts = get_user_texts()

    # Get the summary of the existing proposal
    summary = summarize_pdf("input_documents/")

    # ── Cross-channel intelligence: inject recent call insights ──
    call_insights_text = _get_call_insights_context()

    # Create a new LLMChain
    chain = LLMChain(llm=chat, prompt=prompt)

    # Generate the proposal
    md = chain.run({
        "user_queries": texts,
        "existing_proposal": summary,
        "call_insights": call_insights_text,
    })

    # Save the proposal (legacy single-doc store)
    save_proposal({"proposal": md})

    # Save with a UUID for buyer-facing sharing
    db = Database(APP_DB_NAME)
    docs_list = documents_used or files
    html = markdown_to_html_file(md)
    proposal_id = db.save_proposal_with_id(
        html_content=html,
        markdown_content=md,
        created_by=created_by,
        documents_used=docs_list,
    )

    # Best-effort HubSpot trace for generated proposals.
    try:
        sync_proposal_generation_to_crm(created_by, proposal_id, created_by, docs_list)
    except Exception:
        pass

    # Save the proposal as an HTML file
    with open("all_documents/proposal.html", "w", encoding="utf-8") as file:
        file.write(html)

    # Convert the proposal to PDF
    response = requests.post("https://md-to-pdf.fly.dev", data={"markdown": md})
    if response.status_code == 200:
        with open("all_documents/proposal.pdf", "wb") as f:
            f.write(response.content)
    else:
        print(f"Conversion to pdf failed with status code {response.status_code}")

    return {"message": "Proposal generated successfully.", "proposal_id": proposal_id}


def _get_call_insights_context() -> str:
    """Pull the last 3 call summaries and format them as context for the LLM."""
    try:
        db = Database(APP_DB_NAME)
        calls = db.get_recent_call_insights(limit=3)
        if not calls:
            return "No recent call insights available."
        lines = []
        for c in calls:
            lines.append(f"- Call with {c.get('phone_number', 'unknown')}: {c.get('summary', '')[:300]}")
        return "\n".join(lines)
    except Exception:
        return "No recent call insights available."


def summarize_pdf(path):
    loader = PyPDFDirectoryLoader(path)
    docs = loader.load_and_split()
    chain = load_summarize_chain(chat, chain_type="refine")
    summary = chain.run(docs)
    return summary


def get_user_texts():
    db = Database(APP_DB_NAME)
    return db.get_texts_by_user_id("human")


def save_proposal(proposal_data):
    db = Database(APP_DB_NAME)
    db.save_proposal(proposal_data)


prompt = ChatPromptTemplate.from_template(
    template="""You work as the head of sales for a corporation. Your major goal is to enhance corporate revenue by creating
New sales proposals. Use the greatest sales strategies you know to boost sales.
You must develop new sales proposals based on user inquiries and existing proposals.
The proposal should include at least the following (one page per topic, verbosely):
1) Information about the firm
2) Clients
3) Our Solution
4) Benefits of Us
5) Pricing
6) Timeline(optional)
7) The next steps should include contact information and other relevant information.
You should include any other details that you believe are necessary.
The proposal should be in Markdown format.
To make the proposal more understandable, include headers, emphasis, lists, and tables wherever they are necessary.
While listing items, ensure they are tabulated and have appropriate titles.
Ensure that the table is properly formatted, with each row on a separate line.
Use the correct header sizes to make the proposal visually appealing and readable.
The following are the user's queries:
Only create according to these if you believe they are relevant.
    ---------------------------
        {user_queries}.
    -----------------------------
    This is the summary of the existing proposal:
    ---------------------------------
        {existing_proposal}.
    ---------------------------------
    These are recent call insights from live sales conversations — use them to address likely objections and emphasise relevant benefits:
    ---------------------------------
        {call_insights}
    ---------------------------------


    """
)

if __name__ == "__main__":
    generate_proposal()
