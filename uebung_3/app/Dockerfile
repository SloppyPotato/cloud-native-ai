FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Standard: agent.py. Anderes Skript: docker compose run --rm app messen.py
ENTRYPOINT ["python"]
CMD ["agent.py"]
