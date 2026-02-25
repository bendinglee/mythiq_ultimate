FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic==2.* sqlite-utils redis qdrant-client
COPY app /app/app
RUN mkdir -p /app/state /app/logs
EXPOSE 7777
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","7777"]
