FROM python:3.7

RUN apt-get update && apt-get -y install curl unzip vim nano
# RUN mount <path_to_nfs> /data

RUN python -m pip install --upgrade pip
WORKDIR /usr/share/sherlock
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD [ "python", "./frontend.py" ]