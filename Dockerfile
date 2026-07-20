FROM python:3.13-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code-only changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Uploaded product photos should survive container recreation.
VOLUME ["/app/static/uploads"]

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Runtime configuration (pass at `docker run` time, none are baked into the image):
#   SECRET_KEY         required in production — a random value signs sessions and CSRF tokens.
#                      e.g. docker run -e SECRET_KEY=$(python3 -c "import secrets;print(secrets.token_hex(32))") ...
#   ANTHROPIC_API_KEY  optional — without it, the AI diagnostic/chatbot fall back to the local
#                      rule-based engine (see domain_answer() / ml_model.py) instead of Claude.
#   STRIPE_SECRET_KEY  optional — without it, checkout falls back to the simulated payment
#                      flow. Use a Stripe *test* secret key (sk_test_...) for a real but
#                      no-money-moves Stripe Checkout integration.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]
