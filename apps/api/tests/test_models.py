from django.test import TestCase
import pytest
import re
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.api.models import UploadedFile, FileTextExtraction, Conversation, Message
import numpy as np

@pytest.mark.django_db
class TestUploadedFile:
    def test_create_uploaded_file(self):
        """
        Test creating an UploadedFile instance:
        - Verify the file_name is set correctly
        - Check if the file is uploaded and named correctly
        - Ensure the string representation is the file name
        """
        file = SimpleUploadedFile("test_file.pdf", b"file_content")
        uploaded_file = UploadedFile.objects.create(
            file_name="test_file.pdf",
            file=file
        )
        assert uploaded_file.file_name == "test_file.pdf"
        assert re.match(r'pdf_files/test_file_[a-zA-Z0-9]{7}\.pdf', uploaded_file.file.name)
        assert str(uploaded_file) == "test_file.pdf"

@pytest.mark.django_db
class TestFileTextExtraction:
    def test_create_file_text_extraction(self, uploaded_file):
        """
        Test creating a FileTextExtraction instance:
        - Verify all fields are set correctly (extracted_text, chunk_index, page_number, etc.)
        - Check if the metadata is stored as expected
        - Ensure the string representation is the id_external
        """

        test_vector = generate_test_vector(dimensions=768)
        extraction = FileTextExtraction.objects.create(
            source_file=uploaded_file,
            extracted_text="Test extracted text",
            chunk_index=1,
            page_number=1,
            chunk_start=0,
            chunk_end=20,
            embeddings_together_m2_bert_80M_2k_retrieval=test_vector
        )
        assert extraction.extracted_text == "Test extracted text"
        assert extraction.chunk_index == 1
        assert extraction.page_number == 1
        assert extraction.chunk_start == 0
        assert extraction.chunk_end == 20
        assert extraction.embeddings_together_m2_bert_80M_2k_retrieval == test_vector
        assert str(extraction) == str(extraction.id_external)

@pytest.mark.django_db
class TestConversation:
    def test_create_conversation(self, uploaded_file):
        """
        Test creating a Conversation instance:
        - Verify the associated_file is set correctly
        - Ensure the string representation is the id_external
        """
        conversation = Conversation.objects.create(associated_file=uploaded_file)
        assert conversation.associated_file == uploaded_file
        assert str(conversation) == str(conversation.id_external)

@pytest.mark.django_db
class TestMessage:
    def test_create_message(self, conversation):
        """
        Test creating a Message instance:
        - Verify the conversation, role, and content are set correctly
        - Ensure the string representation is the id_external
        """
        message = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Test message content"
        )
        assert message.conversation == conversation
        assert message.role == "user"
        assert message.content == "Test message content"
        assert str(message) == str(message.id_external)

@pytest.fixture
def uploaded_file():
    """
    Fixture to create and return an UploadedFile instance for use in tests
    """
    file = SimpleUploadedFile("test_file.pdf", b"file_content")
    return UploadedFile.objects.create(file_name="test_file.pdf", file=file)

@pytest.fixture
def conversation(uploaded_file):
    """
    Fixture to create and return a Conversation instance for use in tests
    """
    return Conversation.objects.create(associated_file=uploaded_file)

def generate_test_vector(dimensions=768):
    """Generate a random vector with the specified number of dimensions."""
    return list(np.random.rand(dimensions))