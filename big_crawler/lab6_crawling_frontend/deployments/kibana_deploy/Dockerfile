FROM docker.elastic.co/kibana/kibana-oss:6.5.4

WORKDIR /usr/share/kibana
# copy the certificate
COPY 2e1c46d0-ce0b-11e8-b230-ced9d81cd3f4 certs/2e1c46d0-ce0b-11e8-b230-ced9d81cd3f4
# and the configuration file
COPY kibana.yml config/kibana.yml
EXPOSE 5601

# start the kibana server
CMD ["./bin/kibana"]