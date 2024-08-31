from apps.api.models import (
    Conversation, Message, ChatMessagesSchema, PdfInquestOutputSchema,
    UploadedFile, ChatMessageSchema, PdfInquestContinueOutputSchema, ConversationSchema,
    ConversationListSchema, 
)
from common.together import generate_together_chat_completions, generate_together_text_embeddings
from asgiref.sync import sync_to_async, async_to_sync
from ninja.files import UploadedFile as UploadedFileNinja
from common.helpers import similarity_search
from common.extraction import text_extractor
from apps.api.utils.pdf_utils import create_text_extraction
from uuid import UUID
from django.db.models import Q


async def create_conversation(chat: str, file: UploadedFileNinja):
    """
    Create a new conversation with an associated PDF file and initial chat message.

    This function handles the creation of a conversation by saving the uploaded file,
    generating text embeddings for the initial chat message, and creating a message
    entry for the user. It returns the created conversation and the saved file.

    Args:
        chat (str): The initial chat message to start the conversation.
        file (UploadedFileNinja): The uploaded PDF file associated with the conversation.

    Returns:
        tuple: A tuple containing the created Conversation object and the UploadedFile object.

    Raises:
        ValueError: If there is an error during the creation process.
    """
    try:
        saved_file = await UploadedFile.objects.acreate(file_name=file.name, file=file)
        conversation = await Conversation.objects.acreate(associated_file=saved_file)
        chat_embeddings = await generate_together_text_embeddings(chat)
        await Message.objects.acreate(
            conversation=conversation,
            role='user',
            content=chat,
            embeddings_together_m2_bert_80M_2k_retrieval=chat_embeddings.embeddings
        )
        return conversation, saved_file, chat_embeddings
    except Exception as e:
        raise ValueError(f"Error creating conversation: {str(e)}")

async def add_pdf_to_conversation(conversation_id: str, uploaded_file):
    """
    Add a PDF file to an existing conversation.

    This function retrieves the conversation by its external ID and adds the provided
    uploaded file to the conversation's associated files. It then saves the updated
    conversation.

    Args:
        conversation_id (str): The unique identifier of the conversation to which the file will be added.
        uploaded_file: The uploaded file to be associated with the conversation.

    Returns:
        str: The external ID of the updated conversation.

    Raises:
        ValueError: If there is an error while adding the PDF to the conversation.
    """
    try:
        conversation = await Conversation.objects.get(id_external=conversation_id)
        conversation.associated_file.add(uploaded_file)
        conversation.save()
        return conversation.id_external
    except Exception as e:
        raise ValueError(f"Error adding PDF to conversation.")

async def generate_chat_response(chat: str, context: list, conversation: Conversation):
    """
    Generate a chat response based on the user's message and the conversation context.

    This function constructs a chat message schema from the user's input and the
    prior context, sends it to the chat completion model, and saves the assistant's
    response as a new message in the conversation.

    Args:
        chat (str): The user's chat message for which a response is to be generated.
        context (list): A list of prior context messages relevant to the conversation.
        conversation (Conversation): The conversation object to which the response will be added.

    Returns:
        Message: The newly created message object containing the assistant's response.

    Raises:
        ValueError: If the chat response is empty or if there is an error during the generation process.
    """
    try:
        context_str = ""
        for chunk in context:
            context_str += chunk
        
        #Returns ChatMessagesSchema
        chat_messages = await generate_chat_messages_new(chat=chat, context=context, conversation_id=conversation.id_external)
        
        #Returns ChatOutputSchema from ChatMessagesSchema
        chat_response = await generate_together_chat_completions(
            messages=chat_messages,
            conversation_id=conversation.id_external
        )
        
        if not chat_response.response:
            raise ValueError("Empty response from chat completion")
        
        chat_response_message = await Message.objects.acreate(
            conversation=conversation,
            role='assistant',
            content=chat_response.response
        )
        
        await conversation.messages.aadd(chat_response_message)
        return chat_response_message

    except Exception:
        raise ValueError("Error generating chat response.")

async def get_conversation_messages(conversation_id: str) -> list[Message]:
    """
    Retrieve the messages from a conversation.

    This function retrieves all messages from a conversation based on the provided
    conversation ID. It returns the messages in the order they were created.

    Args:
        conversation_id (str): The unique identifier of the conversation.

    Returns:
        list[Message]: A list of messages from the conversation.

    Raises:
        ValueError: If there is an error while retrieving the messages.
    """
    try:
        conversation = await Conversation.objects.aget(id_external=conversation_id)
        prior_context = await sync_to_async(list)(conversation.messages.all().order_by("created_at"))  # Use sync_to_async to await the queryset
        return prior_context
    except Exception as e:
        raise ValueError("Error getting conversation messages.")
    
async def generate_chat_messages_new(chat: str, context: list[str], conversation_id: str) -> ChatMessagesSchema:
    """
    Generate a new set of chat messages for the conversation.

    This function constructs a chat message schema that includes system prompts,
    the user's current message, and prior context messages. It prepares the data
    for sending to the chat completion model.

    Args:
        chat (str): The user's current chat message.
        context (list[str]): A list of context messages to provide background for the chat.
        conversation_id (str): The unique identifier of the conversation.

    Returns:
        ChatMessagesSchema: A schema containing the structured chat messages.

    Raises:
        ValueError: If there is an error while generating the chat messages.
    """
    system_prompt = "You are a PDF file agent. You are tasked with helping the user understand and answer questions about the contents of the PDF file, or parts of a PDF file, which I am sending to you in chunked strings in the Role System Content follow this prompt."
    prior_context = await get_conversation_messages(conversation_id)
    messages = [
        ChatMessageSchema(role="system", content=system_prompt),
        ChatMessageSchema(role="system", content=' '.join(context)),
    ]
    
    # Add prior context messages
    for prior_message in prior_context:
        if prior_message.role == "user":
            messages.append(ChatMessageSchema(role="user", content=prior_message.content))
        elif prior_message.role == "assistant":
            messages.append(ChatMessageSchema(role="assistant", content=prior_message.content))
    return ChatMessagesSchema(messages=messages)

async def start_pdf_inquest_helper(chat: str, file: UploadedFileNinja) -> PdfInquestOutputSchema:
    """
    Initiate a PDF inquest by creating a conversation and extracting text from the PDF.

    This function creates a new conversation with the provided chat message and PDF file,
    extracts text from the PDF, generates embeddings for the chat query, and performs
    a similarity search to find relevant chunks of text. It returns the results in a
    structured output schema.

    Args:
        chat (str): The initial chat message to start the inquest.
        file (UploadedFileNinja): The uploaded PDF file to be analyzed.

    Returns:
        PdfInquestOutputSchema: A schema containing the conversation ID, response, file ID,
        and text extraction IDs.

    Raises:
        ValueError: If there is an error during the inquest process.
    """
    conversation, uploaded_file, chat_embeddings = await create_conversation(chat, file)
    file_extracted_text = await text_extractor(file)
    
    text_extraction_ids = []
    
    for chunk in file_extracted_text:
        _, extraction_id = await create_text_extraction(uploaded_file, chunk)
        text_extraction_ids.append(extraction_id)
    
    query_embeddings = chat_embeddings

    relevant_chunks = await similarity_search(query_embeddings.embeddings, limit=5, document_id=uploaded_file.id_external)
    context = [chunk.extracted_text for chunk in relevant_chunks]
    
    chat_response = await generate_chat_response(chat, context, conversation)
    
    return PdfInquestOutputSchema(
        conversation_id=conversation.id_external,
        response=chat_response.content,
        file_id=uploaded_file.id_external,
        text_extractions=text_extraction_ids
    )

async def continue_pdf_inquest_helper(chat: str, conversation_id: UUID) -> PdfInquestContinueOutputSchema:
    """
    Continue an ongoing PDF inquest with a new chat message.

    This function retrieves the existing conversation by its ID, generates embeddings
    for the new chat message, performs a similarity search to find relevant text chunks,
    and generates a response based on the updated context. It returns the response in a
    structured output schema.

    Args:
        chat (str): The new chat message to continue the conversation.
        conversation_id (UUID): The unique identifier of the ongoing conversation.

    Returns:
        PdfInquestContinueOutputSchema: A schema containing the conversation ID and the
        assistant's response.

    Raises:
        ValueError: If there is an error during the continuation of the inquest.
    """
    conversation = await Conversation.objects.select_related('associated_file').aget(id_external=conversation_id)
    file = conversation.associated_file

    query_embeddings = await generate_together_text_embeddings(chat)
    message = await Message.objects.acreate(
        conversation=conversation,
        role='user',
        content=chat,
        embeddings_together_m2_bert_80M_2k_retrieval=query_embeddings.embeddings
    )

    relevant_chunks = await similarity_search(query_embeddings.embeddings, limit=5, document_id=file.id_external)
    context = [chunk.extracted_text for chunk in relevant_chunks]

    chat_response_message = await generate_chat_response(chat, context, conversation)
    
    return PdfInquestContinueOutputSchema(
        conversation_id=conversation.id_external,
        response=chat_response_message.content,
    )

def get_conversations_helper() -> ConversationListSchema:
    conversations = Conversation.objects.all()
    
    conversations_list = [
        ConversationSchema(
            id=conversation.id_external,
            created_at=str(conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')),
            updated_at=str(conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S')),
            associated_file=str(conversation.associated_file.file_name) if conversation.associated_file else None
        ) for conversation in conversations
    ]
    return conversations_list

def delete_conversation_helper(conversation_id: UUID) -> UUID:
    conversation = Conversation.objects.get(id_external=conversation_id)
    conversation.delete()
    return conversation.id_external

def get_conversation_messages_helper(conversation_id: UUID) -> list[ChatMessageSchema]:
    conversation = Conversation.objects.get(id_external=conversation_id)
    messages = conversation.messages.filter(Q(role='user') | Q(role='assistant'))
    return messages

def delete_conversation_message_helper(conversation_id: UUID, message_id: UUID) -> UUID:
    conversation = Conversation.objects.get(id_external=conversation_id)
    message = conversation.messages.objects.get(id_external=message_id)
    message.delete()
    return message.id_external

