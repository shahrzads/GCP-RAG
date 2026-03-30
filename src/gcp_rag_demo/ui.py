"""Simple Streamlit UI for uploading PDFs and asking questions."""

from gcp_rag_demo.config import get_settings
from gcp_rag_demo.data_io import source_document_from_pdf_bytes
from gcp_rag_demo.pipeline import ingest_documents
from gcp_rag_demo.pipeline import query_documents
from gcp_rag_demo.storage import GCSArtifactStore


def main() -> None:
    """Render the upload-and-query Streamlit app."""
    import streamlit as st

    st.set_page_config(page_title="GCP RAG PDF Demo", layout="wide")
    st.title("GCP RAG PDF Demo")
    st.caption("Upload PDFs, build an index in GCP, and ask grounded questions.")

    settings = get_settings()
    if not settings.bucket_name:
        st.error("GCS_BUCKET_NAME must be configured before using the UI.")
        return

    index_blob = settings.index_artifact_blob
    preview_blob = settings.chunk_preview_blob
    vector_search_prefix = settings.vector_search_artifact_prefix
    source_prefix = "{0}/ui".format(settings.source_artifact_prefix.strip("/ "))

    st.subheader("1. Upload PDFs")
    uploaded_files = st.file_uploader(
        "Choose one or more PDF files",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if st.button("Build Index", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Upload at least one PDF file before building the index.")
        else:
            store = GCSArtifactStore(project_id=settings.project_id, bucket_name=settings.bucket_name)
            documents = []
            raw_uris = []
            for uploaded_file in uploaded_files:
                content = uploaded_file.getvalue()
                source_blob = "{0}/{1}".format(source_prefix, uploaded_file.name)
                source_uri = store.upload_bytes(source_blob, content, content_type="application/pdf")
                raw_uris.append(source_uri)
                documents.append(
                    source_document_from_pdf_bytes(
                        filename=uploaded_file.name,
                        content=content,
                        source_uri=source_uri,
                    )
                )

            result = ingest_documents(
                documents,
                settings,
                output_blob=index_blob,
                preview_blob=preview_blob,
                vector_search_prefix=vector_search_prefix,
            )
            st.session_state["index_blob"] = index_blob
            st.session_state["ingest_result"] = result
            st.session_state["raw_uris"] = raw_uris

    if "ingest_result" in st.session_state:
        result = st.session_state["ingest_result"]
        st.success("Index built successfully.")
        st.write("Index artifact:", result.index_uri)
        st.write("Chunk preview:", result.preview_uri)
        st.write("Vector input:", result.vector_input_uri)
        st.write("Vector index:", result.vector_index_name)
        st.write("Vector endpoint:", result.vector_endpoint_name)
        st.write("Uploaded PDFs:")
        for uri in st.session_state.get("raw_uris", []):
            st.write("-", uri)

    st.subheader("2. Ask Questions")
    question = st.text_input("Ask a question about your uploaded PDFs")
    retrieval_only = st.checkbox("Show retrieval only", value=False)

    if st.button("Ask", use_container_width=True):
        current_index_blob = st.session_state.get("index_blob")
        if not current_index_blob:
            st.warning("Build an index first.")
        elif not question.strip():
            st.warning("Enter a question before querying.")
        else:
            result = query_documents(
                question.strip(),
                settings,
                index_blob=current_index_blob,
                top_k=3,
                retrieval_only=retrieval_only,
            )
            if result.answer is not None:
                st.markdown("**Answer**")
                st.write(result.answer)

            st.markdown("**Retrieved Chunks**")
            for index, item in enumerate(result.results, start=1):
                st.markdown(
                    "{0}. `{1}` score={2:.4f}".format(index, item.chunk_id, item.score)
                )
                st.write(item.source_uri)
                st.write(item.text)


if __name__ == "__main__":
    main()
