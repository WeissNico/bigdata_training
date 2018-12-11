FROM python:3.7-alpine

## add the edge-community repository
RUN echo "@edgecommunity http://nl.alpinelinux.org/alpine/edge/community" \
    >> /etc/apk/repositories
RUN apk update 
RUN apk add build-base libxml2-dev libxslt-dev \
    libssl1.0 openssl-dev \
    curl unzip vim nano \
    wkhtmltopdf@edgecommunity poppler-utils

RUN python -m pip install --upgrade pip
WORKDIR /usr/share/sherlock
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

## Link the wkhtmltopdf wrapper appropriately. THIS IS ONLY NECESSARY FOR
## the non-alpine image.
# RUN chmod +x wkhtmltopdf.sh
# RUN ln -s /usr/local/bin/wkhtmltopdf wkhtmltopdf.sh
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