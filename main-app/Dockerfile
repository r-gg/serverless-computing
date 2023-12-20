FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["git", "clone", "https://github.com/apache/kafka.git" "kafka"]

CMD ["python","app.py"]
