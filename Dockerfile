FROM python:3

RUN apt-get update && apt-get install avahi-utils -y

RUN mkdir -p /app/config

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./src/main.py"]
