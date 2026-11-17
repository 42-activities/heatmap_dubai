FROM python:3.11-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/app ./app
