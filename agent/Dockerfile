FROM python:3.11-slim

WORKDIR /app

# Copy entire project
COPY . .

# Install dependencies
RUN pip install --no-cache-dir \
    langgraph \
    langchain \
    langchain-groq \
    groq \
    fastapi \
    uvicorn \
    kubernetes \
    python-dotenv \
    pydantic

EXPOSE 8000

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
