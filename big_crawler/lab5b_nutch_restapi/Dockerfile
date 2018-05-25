FROM pure/nutch-mongo:alpine
RUN apk update
RUN apk add python3 py3-pip openrc
RUN pip3 install flask
ADD rest.py /nutch/rest.py
CMD [ "/usr/bin/python3", "/nutch/rest.py" ]
# http://localhost:18081/seed?seed=www.duesseldorf.de
# http://localhost:18081/run