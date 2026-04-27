# base image
FROM python:3.9-slim

# working directory
WORKDIR /app

# copy files
COPY . /app

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# expose port
EXPOSE 5000

# environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# run application
CMD ["flask", "run"]
