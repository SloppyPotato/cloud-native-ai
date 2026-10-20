FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Standard: einordnen.py. Anderes Skript: docker compose run --rm app angriff.py
ENTRYPOINT ["python"]
CMD ["einordnen.py"]
