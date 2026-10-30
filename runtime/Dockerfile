FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir .
EXPOSE 8081
CMD ["python", "-m", "studio_runtime.worker", "start"]
