from common.together import generate_together_text_embeddings, generate_together_extraction_embeddings
from apps.api.models import FileTextExtraction, UploadedFile, ChunkedTextExtractionSchema, EmbeddingsListSchema
from typing import BinaryIO
from common.extraction import text_extractor
from ninja.files import UploadedFile as UploadedFileNinja

async def extract_pdf_text(file: BinaryIO):
    """
    Extract text from a PDF file.

    This function utilizes a text extractor to read and extract text content 
    from the provided PDF file.

    Args:
        file (BinaryIO): A binary file-like object representing the PDF from which to extract text.

    Returns:
        list: A list of dictionaries containing the extracted text chunks and their metadata.

    Raises:
        ValueError: If an error occurs during the text extraction process.
    """
    try:
        return await text_extractor(file)
    except Exception as e:
        raise ValueError(f"Error extracting text.")

async def create_text_extraction(uploaded_file, chunk):
    """
    Create a text extraction entry in the database.

    This function generates embeddings for a given text chunk and creates a new
    entry in the FileTextExtraction model. It associates the extracted text with
    the provided uploaded file and stores relevant metadata.

    Args:
        uploaded_file (UploadedFile): The uploaded file associated with the text extraction.
        chunk (dict): A dictionary containing the text chunk and its associated metadata.

    Returns:
        tuple: A tuple containing the extracted text chunk and the external ID of the created
        FileTextExtraction instance.

    Raises:
        ValueError: If an error occurs during the creation of the text extraction entry.
    """
    try:
        embeddings = await generate_together_text_embeddings(chunk['chunk'])
        file_text_extraction = await FileTextExtraction.objects.acreate(
            source_file=uploaded_file,
            extracted_text=chunk['chunk'],
            embeddings_together_m2_bert_80M_2k_retrieval=embeddings.embeddings,
            chunk_index=chunk['chunk_index'],
            page_number=chunk['page_number'],
            chunk_start=chunk['chunk_start'],
            chunk_end=chunk['chunk_end'],
            metadata=chunk['metadata']
        )
        return chunk['chunk'], file_text_extraction.id_external
    except Exception as e:
        raise ValueError(f"Error creating text extractions: {e}")

async def extract_text_from_pdf_helper(file: UploadedFileNinja) -> ChunkedTextExtractionSchema:
    """
    Extract text from a PDF file and create corresponding database entries.

    This function handles the extraction of text from the provided PDF file, creates
    a new UploadedFile entry in the database, and saves each extracted text chunk
    as a FileTextExtraction entry. It returns a schema containing the extracted text.

    Args:
        file (UploadedFileNinja): The uploaded PDF file from which to extract text.

    Returns:
        ChunkedTextExtractionSchema: A schema containing the extracted text chunks.

    Raises:
        ValueError: If an error occurs during the extraction or database entry creation process.
    """
    new_file = await UploadedFile.objects.acreate(file_name=file.name, file=file)
    extracted_text = await extract_pdf_text(file)

    for chunk in extracted_text:
        await FileTextExtraction.objects.acreate(
            source_file=new_file,
            extracted_text=chunk['chunk'],
            chunk_index=chunk['chunk_index'],
            page_number=chunk['page_number'],
            chunk_start=chunk['chunk_start'],
            chunk_end=chunk['chunk_end'],
            metadata=chunk['metadata']
        )
    return ChunkedTextExtractionSchema(
        extracted_text=extracted_text
    )

async def extract_and_generate_embeddings_helper(file: UploadedFileNinja) -> EmbeddingsListSchema:
    """
    Extract text from a PDF file and generate embeddings for each chunk.

    This function creates a new UploadedFile entry for the provided PDF file, extracts
    text from the file, and generates embeddings for each extracted text chunk. It
    saves the embeddings and associated metadata in the database and returns a list
    of generated embeddings.

    Args:
        file (UploadedFileNinja): The uploaded PDF file from which to extract text and generate embeddings.

    Returns:
        EmbeddingsListSchema: A schema containing the list of generated embeddings.

    Raises:
        ValueError: If an error occurs during the extraction, embedding generation, or database entry creation process.
    """
    db_file = await UploadedFile.objects.acreate(
            file_name=file.name,
            file=file
        )

    # Extract text from the PDF file
    extracted_text = await extract_pdf_text(db_file.file)

    embeddings_list = []
    for chunk in extracted_text:
        # Generate embeddings for each chunk
        embeddings_schema = await generate_together_extraction_embeddings(ChunkedTextExtractionSchema(extracted_text=[chunk]))
        embeddings_list.extend(embeddings_schema.embeddings)

        # Create PdfTextExtraction instance for each chunk
        await FileTextExtraction.objects.acreate(
            source_file=db_file,
            extracted_text=chunk['chunk'],
            chunk_index=chunk['chunk_index'],
            page_number=chunk['page_number'],
            chunk_start=chunk['chunk_start'],
            chunk_end=chunk['chunk_end'],
            metadata=chunk['metadata'],
            embeddings_together_m2_bert_80M_2k_retrieval=embeddings_schema.embeddings[0].embeddings
        )

    return EmbeddingsListSchema(embeddings=embeddings_list)