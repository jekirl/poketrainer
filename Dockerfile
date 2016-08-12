FROM python:2.7

#requirements
COPY requirements.txt /

#update base and install prerequisites
RUN apt-get update && apt-get install protobuf-compiler -y
RUN pip install -r requirements.txt

#libencrypt.so
RUN wget http://pgoapi.com/pgoencrypt.tar.gz
RUN tar -xf pgoencrypt.tar.gz
RUN make -C /pgoencrypt/src
RUN mv /pgoencrypt/src/libencrypt.so /

#files
COPY docker_launch.sh /
COPY pokecli.py /
COPY web.py /
COPY CLSniper.py /

#folders
COPY ./helper /helper
COPY ./library /library
COPY ./poketrainer /poketrainer
COPY ./resources /resources
COPY ./web /web
VOLUME /data_dumps

#launch script
RUN chmod +x docker_launch.sh
ENTRYPOINT [ "bash", "docker_launch.sh" ]
