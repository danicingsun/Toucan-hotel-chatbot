# Dockerfile (Rasa server)
FROM rasa/rasa:3.6.20-full

WORKDIR /app
COPY . .

# Install extra python deps (for custom components)
RUN pip install --no-cache-dir -r requirements.txt || true

# If you store model in remote storage, include a start script that downloads it
# and extracts into /app/models. Otherwise copy models into the image at build.
COPY models /app/models

# Expose recommended port. Render will give an env $PORT which we set in render.yaml or env vars.
EXPOSE 10000

# Use a small wrapper to honor PORT env var or fallback to 10000
CMD ["bash", "-lc", "rasa run --enable-api --cors \"*\" --port ${PORT:-10000} --model models"]