FROM python:3.12-slim


ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app


# Install dependencies
COPY requirements-server.txt .
RUN pip install -r requirements-server.txt

# Copy the rest of the code
COPY app.py .

RUN useradd --create-home appuser
USER appuser

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]