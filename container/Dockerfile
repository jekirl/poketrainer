FROM python:2.7

RUN apt-get update && apt-get install protobuf-compiler -y

#files
COPY ./ /
COPY ./container/launch.sh /
#folders
COPY ./pgoapi /pgoapi
COPY ./static /static
COPY ./templates /templates

VOLUME /data_dumps

RUN pip install -r requirements.txt

RUN chmod +x launch.sh
ENTRYPOINT [ "bash", "launch.sh" ]
