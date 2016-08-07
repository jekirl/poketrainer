FROM python:2.7

#files
COPY requirements.txt /
COPY container/launch.sh /
COPY ./pokecli.py /
COPY ./web.py /
COPY ./listener.py /
COPY ./PoGoPokeLvl.tsv /
COPY ./libencrypt.so /lib/
COPY GAME_MASTER_POKEMON_v0_2.tsv /
COPY GAME_ATTACKS_v0_1.tsv /
COPY pokemon.en.json /
#folders
COPY ./pgoapi /pgoapi
COPY ./static /static
COPY ./templates /templates
VOLUME /data_dumps
#update base and install prerequisites
RUN apt-get update && apt-get install protobuf-compiler -y
RUN pip install -r requirements.txt
#libencrypt.so
RUN wget http://pgoapi.com/pgoencrypt.tar.gz
RUN tar -xf pgoencrypt.tar.gz
RUN make -C /pgoencrypt/src
RUN mv /pgoencrypt/src/libencrypt.so /lib
#launch script
RUN chmod +x launch.sh
ENTRYPOINT [ "bash", "launch.sh" ]
