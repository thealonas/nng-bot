FROM python:alpine
EXPOSE 1231
WORKDIR /app
COPY . .
RUN apk --no-cache add gcc libc-dev libffi-dev git
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1231"]
