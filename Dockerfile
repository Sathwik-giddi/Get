FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ agent/
COPY api/ api/
COPY skills/ skills/
COPY demo/make_dataset.py demo/
COPY web/package.json web/package-lock.json ./web/
RUN cd web && npm ci
COPY web/ web/
RUN cd web && npm run build

EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
