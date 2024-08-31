from ninja import NinjaAPI
from apps.api.api import router as api_router
from apps.api.docsbase import Rapidoc, Elements, Scalar

api = NinjaAPI(
    title="imperai",
    description="imperai provides tools to power custom LLM RAG applications. Process data, build custom models or bring your own, manage prompting, and iterate as you scale.",
    version="0.1.0",
    docs=Scalar(),
    docs_url="/v1/docs",
)

api.add_router("/v1", api_router)