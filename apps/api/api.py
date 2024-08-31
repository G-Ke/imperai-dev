from ninja import Router, File
from ninja.errors import HttpError
from ninja.files import UploadedFile as UploadedFileNinja

from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from .models import (
    TextInputSchema,ChunkedTextExtractionSchema,
    PdfInquestOutputSchema, PdfInquestContinueOutputSchema,
    ConversationListSchema, ConversationSchema,
    EmbeddingsListSchema,TextEmbeddingsSchema, Conversation, ChatMessagesSchema
)
from common.together import generate_together_text_embeddings

from common.extraction import text_extractor as text_extractor

from apps.api.utils.pdf_utils import extract_text_from_pdf_helper, extract_and_generate_embeddings_helper
from apps.api.services.conversation_services import (
    start_pdf_inquest_helper, continue_pdf_inquest_helper, get_conversations_helper, delete_conversation_helper, get_conversation_messages_helper,
    delete_conversation_message_helper
)

router = Router()

@router.post(
        "tools/pdf/extract-text", 
        response=ChunkedTextExtractionSchema, 
        tags=['Tools'], 
        description="Extract text from a PDF file.", 
        summary="Extract Text from PDF"
    )
async def extract_text_from_pdf(request, file: UploadedFileNinja = File(...)) -> ChunkedTextExtractionSchema:
    """
    Extract text from a PDF file.

    Args:
        request: The HTTP request object.
        file (UploadedFileNinja): The uploaded PDF file.

    Returns:
        ChunkedTextExtractionSchema: The extracted text in chunks.

    Raises:
        HttpError: If there's an error extracting text from the PDF.
    """
    try:
        return await extract_text_from_pdf_helper(file)
    except Exception:
        raise HttpError(400, "Error extracting text from PDF.")


@router.post(
        "tools/text/generate-embeddings", 
        response=TextEmbeddingsSchema, 
        tags=['Tools'], 
        description="Generate embeddings from raw text.",
        summary="Generate Embeddings from Text"
    )
async def generate_embeddings(request, text: TextInputSchema) -> TextEmbeddingsSchema:
    """
    Generate embeddings from raw text.

    Args:
        request: The HTTP request object.
        text (TextInputSchema): The input text to generate embeddings for.

    Returns:
        TextEmbeddingsSchema: The input text and its corresponding embeddings.
    """
    embeddings = await generate_together_text_embeddings(text.text)
    return TextEmbeddingsSchema(text=text.text, embeddings=embeddings.embeddings)

@router.post(
    "tools/pdf/extract-generate-embeddings",
    response=EmbeddingsListSchema,
    tags=['Tools'],
    description="Extract text from a PDF file and generate embeddings.",
    summary="Generate Embeddings from PDF"
)
async def extract_and_generate_embeddings(request, file: UploadedFileNinja = File(...)) -> EmbeddingsListSchema:
    """
    Extract text from a PDF file and generate embeddings.

    Args:
        request: The HTTP request object.
        file (UploadedFileNinja): The uploaded PDF file.

    Returns:
        EmbeddingsListSchema: A list of text chunks and their corresponding embeddings.

    Raises:
        HttpError: If there's an error extracting text or generating embeddings.
    """
    try:
        return await extract_and_generate_embeddings_helper(file)
    except Exception:
        raise HttpError(400, f"Error extracting and generating embeddings from PDF.")

@router.post(
    "/conversations/start",
    response=PdfInquestOutputSchema,
    summary="Start PDF Conversation",
    description="Supply a chat message and a PDF file to start a conversation with the document.",
    tags=["Conversations"],
)
async def start_pdf_conversation(request, chat_message: str, file: UploadedFileNinja = File(...)) -> PdfInquestOutputSchema:
    """
    Start a conversation with a PDF document.

    Args:
        request: The HTTP request object.
        chat_message (str): The initial chat message to start the conversation.
        file (UploadedFileNinja): The uploaded PDF file to converse about.

    Returns:
        PdfInquestOutputSchema: The response from the PDF inquest, including conversation details.

    Raises:
        HttpError: If there's an error starting the PDF inquest.
    """
    try:
        return await start_pdf_inquest_helper(chat_message, file)
    except Exception:
        raise HttpError(400, "Error starting PDF inquest.")

@router.post(
    "/conversations/{conversation_id}/continue",
    response=PdfInquestContinueOutputSchema,
    description="Supply a chat message and a conversation ID to continue your conversation with the document.",
    summary="Continue PDF Conversation",
    tags=["Conversations"],
)
async def continue_pdf_conversation(
    request, 
    chat_message: str, 
    conversation_id: UUID
) -> PdfInquestContinueOutputSchema:
    """
    Continue a conversation with a PDF document.

    Args:
        request: The HTTP request object.
        chat_message (str): The next chat message in the conversation.
        conversation_id (UUID): The unique identifier for the ongoing conversation.

    Returns:
        PdfInquestContinueOutputSchema: The response from continuing the PDF inquest.

    Raises:
        HttpError: If the conversation is not found or there's a bad request.
    """
    try:
        return await continue_pdf_inquest_helper(chat_message, conversation_id)
    except ObjectDoesNotExist:
        raise HttpError(404, "Conversation with the provided ID not found.")
    except Exception:
        raise HttpError(400, "Bad Request.")

@router.get(
    "/conversations/list",
    response=ConversationListSchema,
    summary="Get All Conversations",
    description="Get all conversations.",
    tags=["Conversations"],
)
def get_all_conversations(request) -> ConversationListSchema:
    """
    Get all conversations.

    Args:
        request: The HTTP request object.

    Returns:
        ConversationListSchema: A list of all conversations.
    """
    try:
        conversations = get_conversations_helper()
        return ConversationListSchema(conversations=conversations)
    except Exception:
        raise HttpError(400, "Failed to get conversations.")
    
@router.delete(
    "/conversations/delete/{conversation_id}",
    description="Delete a conversation by ID.",
    summary="Delete Conversation",
    tags=["Conversations"],
)
def delete_conversation(request, conversation_id: UUID) -> HttpResponse:
    """
    Delete a conversation by ID.

    Args:
        request: The HTTP request object.
        conversation_id (UUID): The unique identifier for the conversation to delete.

    Returns:
        HttpResponse: A UUID and a message indicating the conversation was deleted successfully.

    Raises:
        HttpError: If the conversation is not found or if the request is malformed.
    """
    try:
        deleted_conversation_id = delete_conversation_helper(conversation_id)
        return HttpResponse(status=204, content=f"Conversation {deleted_conversation_id} deleted successfully.")
    except ObjectDoesNotExist:
        raise HttpError(404, "Conversation with the provided ID not found.")
    except Exception:
        raise HttpError(400, "Bad Request.")

@router.get(
    '/conversations/{conversation_id}/messages', 
    response=ChatMessagesSchema,
    summary="Get Conversation Messages",
    description="Get all messages for a conversation.",
    tags=["Conversations"],
)
def get_conversation_messages(request, conversation_id: UUID) -> ChatMessagesSchema:
    """
    Get all messages for a conversation.

    Args:
        request: The HTTP request object.
        conversation_id (UUID): The unique identifier for the conversation.

    Returns:
        ChatMessagesSchema: A list of all messages for the conversation.

    Raises:
        HttpError: If the conversation is not found or there's a bad request.
    """
    try:
        messages = get_conversation_messages_helper(conversation_id)
        return ChatMessagesSchema(messages=messages)
    except ObjectDoesNotExist:
        raise HttpError(404, "Conversation with the provided ID not found.")
    except Exception:
        raise HttpError(400, "Bad Request.")

@router.delete(
    '/conversations/{conversation_id}/messages/{message_id}',
    summary="Delete Message",
    description="Delete a message by ID.",
    tags=["Conversations"],
)
def delete_conversation_message(request, conversation_id: UUID, message_id: UUID) -> HttpResponse:
    """
    Delete a message by ID.

    Args:
        request: The HTTP request object.
        conversation_id (UUID): The unique identifier for the conversation.
        message_id (UUID): The unique identifier for the message to delete.

    Returns:
        HttpResponse: A UUID and a message indicating the message was deleted successfully.

    Raises:
        HttpError: If the conversation or message is not found or if the request is malformed.
    """
    try:
        deleted_message_id = delete_conversation_message_helper(conversation_id, message_id)
        return HttpResponse(status=204, content=f"Message {deleted_message_id} deleted successfully.")
    except ObjectDoesNotExist:
        raise HttpError(404, "Conversation or message with the provided ID not found.")
    except Exception:
        raise HttpError(400, "Bad Request.")