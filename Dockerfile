# Dockerfile (Rasa server)
FROM rasa/rasa:3.6.20-full

# Override Rasa entrypoint so we can run bash or python normally
ENTRYPOINT []

WORKDIR /app
COPY . .

# If you store model in remote storage, include a start script that downloads it
# and extracts into /app/models. Otherwise copy models into the image at build.
COPY models /app/models

# Install extra dependencies as root to avoid permission errors
USER root
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi
USER 1001

# ----------------------------------------
# TRAIN MODEL IN /tmp (Writable on Render)
# ----------------------------------------
RUN mkdir -p /tmp/rasa
RUN rasa train \
    --domain /app/domain.yml \
    --data /app/data \
    --config /app/config.yml \
    --out /tmp/rasa

# Copy model back into the app folder
RUN mkdir -p /app/models && cp /tmp/rasa/*.tar.gz /app/models/

# Expose recommended port. Render will give an env $PORT which we set in render.yaml or env vars.
EXPOSE 10000


# Use a small wrapper to honor PORT env var or fallback to 10000
CMD ["bash", "-lc", "rasa run --enable-api --cors \"*\" --port ${PORT:-10000} --model models"]