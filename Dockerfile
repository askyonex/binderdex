FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && mkdir -p /data
COPY app.py .
COPY static static
ENV HOST=0.0.0.0 DB_PATH=/data/pokedex.db PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 5000
CMD ["python", "app.py"]
