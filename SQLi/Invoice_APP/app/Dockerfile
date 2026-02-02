FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y \
    freetds-dev \
    build-essential \
    && pip install --no-cache-dir flask pymssql

COPY . .

CMD ["python", "app.py"]