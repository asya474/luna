FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QIWI_MOCK_MODE=true

COPY pyproject.toml README.md ./
COPY api ./api
COPY helpers ./helpers
COPY schemas ./schemas
COPY tests ./tests
COPY .env.example ./.env.example

RUN pip install --no-cache-dir -e .

CMD ["pytest", "-m", "not integration and not playwright", "-n", "auto", "-v"]
