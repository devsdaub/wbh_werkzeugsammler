FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Europe/Berlin DATEN=/data

# libgomp1 braucht das XGBoost-Modell von Quartz
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auswertung.py sammler.py vergleich.py web.py ./
COPY static/ ./static/

VOLUME /data
EXPOSE 8000

# gesund, solange der Sammler in der letzten halben Stunde ein Lebenszeichen geschrieben hat
HEALTHCHECK --interval=5m --timeout=10s --start-period=2m \
    CMD python -c "import os,sys,time; sys.exit(time.time()-os.path.getmtime('/data/lebenszeichen.txt')>1800)"

# Oberfläche und Sammler in einem Prozess, der Sammler läuft als Thread
CMD ["uvicorn", "web:app", "--host", "0.0.0.0", "--port", "8000"]
