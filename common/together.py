import os
from together import Together
from apps.api.models import (
    EmbeddingsSchema, ChatMessageSchema, ChatMessagesSchema, 
    ChatOutputSchema, ChunkedTextExtractionSchema, EmbeddingsListSchema, TextInputSchema,
    TextEmbeddingsSchema
)

ENDPOINT_URL="https://api.together.xyz/v1/embeddings"
TOGETHER_API_KEY=os.environ.get("TOGETHER_API_KEY")
TOGETHER_EMBED_MODEL="togethercomputer/m2-bert-80M-2k-retrieval"
TOGETHER_CHAT_MODEL="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

async def generate_together_text_embeddings(text: TextInputSchema) -> TextEmbeddingsSchema:
    """
    Generate text embeddings using the Together API.

    This function takes a text input and generates its corresponding
    embeddings using the Together API. It utilizes the specified embedding model
    to process the input text and returns the embeddings in a structured schema.

    Args:
        text (TextInputSchema): The input text for which embeddings are to be generated.

    Returns:
        TextEmbeddingsSchema: A schema containing the generated embeddings and the original text.

    Raises:
        ValueError: If an error occurs during the embedding generation process.
    """
    together_client = Together(api_key=TOGETHER_API_KEY)
    together_response = together_client.embeddings.create(model=TOGETHER_EMBED_MODEL, input=text)
    return TextEmbeddingsSchema(
        embeddings=together_response.data[0].embedding,
        text=text
    )

async def generate_together_extraction_embeddings(extracted_text: ChunkedTextExtractionSchema) -> EmbeddingsSchema:
    """
    Generate embeddings for extracted text chunks using the Together API.

    This function processes a set of extracted text chunks and generates
    embeddings for each chunk using the Together API. It returns a list of embeddings
    in a structured schema, along with relevant metadata for each chunk.

    Args:
        extracted_text (ChunkedTextExtractionSchema): A schema containing the extracted text chunks.

    Returns:
        EmbeddingsSchema: A schema containing the list of generated embeddings for the text chunks.

    Raises:
        ValueError: If an error occurs during the embedding generation process.
    """
    together_client = Together(api_key=TOGETHER_API_KEY)
    embeddings = []

    for chunk in extracted_text.extracted_text:
        together_response = together_client.embeddings.create(model=TOGETHER_EMBED_MODEL, input=chunk.chunk)
        embeddings.append(EmbeddingsSchema(
            embeddings=together_response.data[0].embedding,
            chunk_index=chunk.chunk_index,
            chunk_start=chunk.chunk_start,
            chunk_end=chunk.chunk_end,
            metadata=chunk.metadata
        ))

    return EmbeddingsListSchema(embeddings=embeddings)

async def generate_together_chat_completions(messages: ChatMessagesSchema, conversation_id: str) -> ChatOutputSchema:
    """
    Generate chat completions using the Together API.

    This function takes a set of chat messages and generates a response
    using the Together API's chat completion model. It returns the generated response
    along with the conversation ID and the last message in a structured output schema.

    Args:
        messages (ChatMessagesSchema): A schema containing the chat messages for the conversation.
        conversation_id (str): The unique identifier of the conversation.

    Returns:
        ChatOutputSchema: A schema containing the conversation ID, the generated response,
        and the last user message.

    Raises:
        ValueError: If an error occurs during the chat completion process.
    """
    together_client = Together(api_key=TOGETHER_API_KEY)

    together_response = together_client.chat.completions.create(
        model=TOGETHER_CHAT_MODEL,
        messages=messages.model_dump()["messages"]
    )
    response_content = together_response.choices[0].message.content
    return ChatOutputSchema(
        conversation_id=conversation_id,
        response=response_content,
        message=messages.messages[-1]
    )

def generate_chat_messages(chat: str, context: list[str]) -> ChatMessagesSchema:
    """
    Construct a structured set of chat messages for the conversation.

    This function generates a list of chat messages, including system prompts and
    the user's current message, formatted for use with the chat completion model.
    It prepares the context and user input for processing.

    Args:
        chat (str): The user's current chat message.
        context (list[str]): A list of context messages to provide background for the chat.

    Returns:
        ChatMessagesSchema: A schema containing the structured chat messages.

    Raises:
        ValueError: If an error occurs during the message construction process.
    """
    system_prompt = "You are a PDF file agent. The NEXT system message is the contents of relevant parts of the PDF file or the PDF file text in its entirety. You are tasked with helping the user understand and answer questions about the contents of the PDF file, or parts of a PDF file, which I am sending to you in chunked strings in the Role System Content follow this prompt."
    messages = [
        ChatMessageSchema(role="system", content=system_prompt),
        ChatMessageSchema(role="system", content=' '.join(context)),
        ChatMessageSchema(role="user", content=chat)
    ]
    return ChatMessagesSchema(messages=messages)
