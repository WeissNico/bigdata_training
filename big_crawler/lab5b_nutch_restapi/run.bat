REM Build: docker build . -t jischebeck/nutch
REM docker push jischebeck/nutch:latest

docker run -it --rm -p 18081:8081 --name nutch jischebeck/nutch:latest /bin/bash