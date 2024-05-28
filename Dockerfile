# Dockerfile
FROM python:3.12

# Instalar Ghostscript
RUN apt-get update && apt-get install -y ghostscript

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "index.py"]
