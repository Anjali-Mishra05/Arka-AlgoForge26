from utils.vectorbase import query_index, PDFProcessor


async def respond(chatbot, message: str, return_sources: bool = False):
    # Fetch relevant document data
    document_data = query_index(message)

    # Call the chatbot's invoke method WITHOUT user_id
    ai_msg = chatbot.invoke(
        text=message,
        document_data=document_data[:150]  # limit to first 150 characters
    )

    if return_sources and document_data:
        # Return individual source chunks (up to 3)
        processor = PDFProcessor()
        chunks = processor.retrieve(message, top_k=3)
        sources = [c[:300] for c in chunks if c.strip()]
        return ai_msg, sources

    if return_sources:
        return ai_msg, []

    return ai_msg
