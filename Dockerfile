FROM python:3.12-slim
WORKDIR /srv/ice-stock
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["waitress-serve", "--port=8000", "--call", "app.main:build"]
