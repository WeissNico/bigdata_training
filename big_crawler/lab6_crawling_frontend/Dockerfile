FROM python:3.7

RUN apt-get update 
RUN apt-get -y install curl unzip vim nano wkhtmltopdf poppler-utils

RUN python -m pip install --upgrade pip
WORKDIR /usr/share/sherlock
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

## SETUP /data PATH
## This must be overriden in the deployment.yml with concrete values.
VOLUME /data
ENV SHERLOCK_UPLOAD_DIR /data/sherlock/uploads
## USE ANOTHER DOCUMENTS INDEX
# ENV SHERLOCK_ES_DOCS_INDEX documents
## USE FLASK IN PRODUCTION MODE
ENV FLASK_ENV PRODUCTION
ENV FLASK_DEBUG false
## EXPOSE port 80
EXPOSE 80

CMD [ "python", "./frontend.py" ]