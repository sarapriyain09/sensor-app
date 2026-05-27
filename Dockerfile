FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PIP_NO_CACHE_DIR=1 \
	PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip \
	&& python -m pip install -r requirements.txt

# Run as non-root (defense-in-depth)
RUN adduser --disabled-password --gecos "" --uid 10001 appuser \
	&& chown -R appuser:appuser /app

USER 10001

CMD ["python", "-u", "app.py"]
