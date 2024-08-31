import io
import re
from typing import BinaryIO, List
from pypdf import PdfReader
from apps.api.models import TextExtractionSchema, ChunkedTextExtractionSchema, TextChunkSchema

async def extract_text(file: BinaryIO) -> TextExtractionSchema:
    """
    Extract text from a PDF file.

    This asynchronous function reads the content of a PDF file and extracts
    all text from its pages. It utilizes the PdfReader to process the PDF
    and returns the extracted text as a structured schema.

    Args:
        file (BinaryIO): A binary file-like object representing the PDF from which to extract text.

    Returns:
        TextExtractionSchema: A schema containing the extracted text from the PDF.

    Raises:
        ValueError: If an error occurs during the reading or extraction process.
    """
    file_content = file.read()
    file_like_object = io.BytesIO(file_content)
    reader = PdfReader(file_like_object)
    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text()
    return extracted_text

async def text_extractor(file: BinaryIO) -> List[dict]:
    """
    Extract structured text chunks from a PDF file.

    This function reads the content of a PDF file, processes it to extract
    text, and organizes the extracted text into chunks with associated metadata.
    It handles empty files and any exceptions that may occur during the extraction.

    Args:
        file (BinaryIO): A binary file-like object representing the PDF from which to extract text.

    Returns:
        List[dict]: A list of dictionaries, each containing a text chunk and its metadata.

    Raises:
        ValueError: If the file is empty or if an error occurs while reading the PDF.
    """
    with file.open() as f:
        file_content = f.read()
        if not file_content:
            raise ValueError("File is empty.")
        file_like_object = io.BytesIO(file_content)
        try:
            reader = PdfReader(file_like_object)
        except Exception as e:
            raise ValueError(f"Error reading PDF: {e}")
        extracted_chunks = []
        chunk_index = 0
        for page_num, page in enumerate(reader.pages, 1):
            text = await clean_pdf_text(page.extract_text())
            chunks = await smart_chunker(text)
            for chunk_num, chunk in enumerate(chunks, 1):
                chunk_start = sum(len(c) for c in chunks[:chunk_num-1])
                chunk_end = chunk_start + len(chunk)
                extracted_chunks.append({
                    "page_number": page_num,
                    "chunk_number": chunk_num,
                    "chunk": chunk,
                    "chunk_index": chunk_index,
                    "chunk_start": chunk_start,
                    "chunk_end": chunk_end,
                    "metadata": {
                        "file_name": file.name,
                        "total_pages": len(reader.pages),
                    }
                })
                chunk_index += 1
        file.close()
    return extracted_chunks

async def clean_pdf_text(text: str) -> str:
    """
    Clean and normalize text extracted from a PDF.

    This function processes the extracted text by removing excessive whitespace,
    non-printable characters, and normalizing quotes and dashes. It ensures that
    the text is clean and ready for further processing.

    Args:
        text (str): The raw text extracted from a PDF.

    Returns:
        str: The cleaned and normalized text.

    Example:
        >>> clean_text = await clean_pdf_text(raw_text)
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    # Normalize quotes and dashes
    text = text.replace('"', '"').replace('"', '"').replace('–', '-')
    return text.strip()

async def smart_chunker(text: str, target_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Chunk text into manageable pieces with specified size and overlap.

    This function splits the provided text into chunks based on sentence boundaries,
    ensuring that each chunk does not exceed a specified target size. It also allows
    for overlap between consecutive chunks to maintain context.

    Args:
        text (str): The text to be chunked.
        target_size (int, optional): The maximum size of each chunk. Defaults to 1000.
        overlap (int, optional): The number of overlapping characters between chunks. Defaults to 100.

    Returns:
        List[str]: A list of text chunks.

    Example:
        >>> chunks = await smart_chunker(long_text)
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        sentence_size = len(sentence)
        if current_size + sentence_size > target_size and current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)
            
            # Calculate overlap
            overlap_text = ' '.join(current_chunk[-2:])  # Use last two sentences for overlap
            current_chunk = [overlap_text]
            current_size = len(overlap_text)
        
        current_chunk.append(sentence)
        current_size += sentence_size

    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks