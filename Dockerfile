FROM python:3.12-slim
WORKDIR /app
COPY server.py domain.py sources.py gmail.py career.py intelligence.py applications.py documents.py ./
COPY static ./static
ENV HOST=0.0.0.0 PORT=8000 CAREER_DB=/data/career.sqlite3 PYTHONUNBUFFERED=1
RUN mkdir /data && chown 1000:1000 /data
USER 1000:1000
EXPOSE 8000
CMD ["python", "server.py"]
