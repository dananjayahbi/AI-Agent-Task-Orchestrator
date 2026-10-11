# M0 placeholder backend image (WP-0.2). Replaced by the real Django image
# in WP-1.1; the compose service name, published port and /health/ready path
# stay the same (MT-0.2-01 risk note).
FROM python:3.12-alpine

# Installed outside /app so the dev bind mount (compose.dev.yaml) can mount
# source at /app without masking the stub.
COPY stub.py /opt/stub/stub.py

EXPOSE 8000 8001

CMD ["python", "/opt/stub/stub.py", "serve"]
