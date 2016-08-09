FROM python:2.7

#files
COPY requirements.txt /
COPY docker_launch.sh /
COPY pokecli.py /
COPY web.py /
#folders
COPY ./helper /helper
COPY ./library /library
COPY ./poketrainer /poketrainer
COPY ./resources /resources
COPY ./web /web
VOLUME /data_dumps
#update base and install prerequisites
RUN apt-get update && apt-get install protobuf-compiler -y
RUN pip install -r requirements.txt
#libencrypt.so
RUN wget http://pgoapi.com/pgoencrypt.tar.gz
RUN tar -xf pgoencrypt.tar.gz
RUN make -C /pgoencrypt/src
RUN mv /pgoencrypt/src/libencrypt.so /
#launch script
RUN chmod +x docker_launch.sh
ENTRYPOINT [ "bash", "docker_launch.sh" ]
