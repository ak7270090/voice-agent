FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir .
# Bake the VAD model into the image so calls do not wait for a download.
RUN python -m studio_voice.worker download-files
EXPOSE 8081
CMD ["python", "-m", "studio_voice.worker", "start"]
