from apps.api.models import FileTextExtraction
from pgvector.django import CosineDistance
from asgiref.sync import sync_to_async
from django.db.models import Q
    
async def similarity_search(query_embeddings: list[float], limit: int = 5, document_id: str = None) -> list[FileTextExtraction]:
    """
    Perform a similarity search using cosine distance on embeddings.

    This function retrieves the top N most similar text extractions
    from the database based on the provided query embeddings. It calculates the
    cosine distance between the query embeddings and the stored embeddings, 
    returning the closest matches up to the specified limit.

    Args:
        query_embeddings (list[float]): A list of float values representing the query embeddings.
        limit (int, optional): The maximum number of similar text extractions to return. Defaults to 5.
        document_id (str, optional): The ID of the document to limit the search to. Defaults to None.
    Returns:
        list[FileTextExtraction]: A list of FileTextExtraction objects that are the closest matches
        to the query embeddings.

    Raises:
        ValueError: If an error occurs during the similarity search process.
    """
    try:
        queryset = FileTextExtraction.objects.annotate(
            distance=CosineDistance("embeddings_together_m2_bert_80M_2k_retrieval", query_embeddings)
        ).filter(Q(source_file__id_external=document_id) if document_id else Q()).order_by("distance")[:limit]
        return await sync_to_async(list)(queryset)
    except Exception as e:
        raise ValueError(f"Error performing similarity search: {e}")
