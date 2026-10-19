FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Standard: hallo_llm.py. Anderes Skript: docker compose run --rm app sampling.py
ENTRYPOINT ["python"]
CMD ["hallo_llm.py"]
