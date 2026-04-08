FROM python:3.12

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY locustfile.py .

# For debugging if locustfile prints/logs
CMD ["tail", "-f", "/dev/null"]
