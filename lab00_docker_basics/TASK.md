# TASK

1) Installiere Docker
2) Installiere eine Beispieldatenbank für die weitere Nutzung

<https://hub.docker.com/r/aa8y/postgres-dataset/>

```
docker pull aa8y/postgres-dataset
docker run -d --name pg-ds -p 5432:5432 aa8y/postgres-dataset:dellstore
```