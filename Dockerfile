FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get install -y --only-upgrade liblzma5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY apps /app/apps
COPY gitplayground /app/gitplayground
COPY templates /app/templates
COPY static /app/static
COPY manage.py /app/manage.py

RUN pip install --upgrade pip && pip install -e .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/')" || exit 1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
