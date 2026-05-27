FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY services/edge_forwarder/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

COPY aws_iot/offline_queue.py /app/aws_iot/offline_queue.py
COPY services/edge_forwarder/app /app/app

RUN adduser --disabled-password --gecos "" --uid 10001 appuser \
    && mkdir -p /var/lib/edge-forwarder \
    && chown -R appuser:appuser /app /var/lib/edge-forwarder

USER 10001

CMD ["python", "-u", "-m", "app.main"]
