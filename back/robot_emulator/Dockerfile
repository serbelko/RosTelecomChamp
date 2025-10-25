FROM python:3.11-slim

WORKDIR /code

COPY emulator.py .

RUN pip install --no-cache-dir requests

CMD ["python", "emulator.py"]