FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

COPY pyproject.toml README.md ./
COPY .streamlit ./.streamlit
COPY src ./src

RUN pip install --upgrade pip && pip install .

EXPOSE 8080

CMD ["sh", "-c", "streamlit run src/gcp_rag_demo/ui.py --server.address=0.0.0.0 --server.port=${PORT:-8080}"]
