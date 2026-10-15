FROM python:3.11-slim
WORKDIR /app
COPY requirements.staging.lock.txt .
RUN pip install --no-cache-dir -r requirements.staging.lock.txt
COPY . .
ENV THANA_ENV=production PORT=8035 THANA_DATA_DIR=/var/lib/thana THANA_PLATFORM_DB=/var/lib/thana/platform.sqlite3
VOLUME /var/lib/thana
EXPOSE 8035
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8035')+'/health',timeout=3)"
CMD ["python", "scripts/start_server.py"]
