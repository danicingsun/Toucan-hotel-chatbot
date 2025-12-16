FROM rasa/rasa:3.6.20-full

# Override Rasa entrypoint
ENTRYPOINT []

WORKDIR /app
COPY . /app

# Copy pre-trained models
COPY models /app/models

# Install extra dependencies
USER root
RUN if [ -f /app/requirements.txt ]; then \
      pip install --no-cache-dir -r /app/requirements.txt; \
    fi
USER 1001

# Render expects this
ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "exec rasa run --enable-api --cors \"*\" -i 0.0.0.0 --port $PORT --model models"]