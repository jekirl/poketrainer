FROM python:2.7

#files
COPY requirements.txt /
COPY container/launch.sh /
COPY ./pokecli.py /
COPY ./web.py /
COPY GAME_MASTER_POKEMON_v0_2.tsv /
COPY GAME_ATTACKS_v0_1.tsv /
COPY pokemon.en.json /
#folders
COPY ./pgoapi /pgoapi
COPY ./static /static
COPY ./templates /templates

VOLUME /data_dumps

RUN apt-get update && apt-get install protobuf-compiler -y
RUN pip install -r requirements.txt

RUN chmod +x launch.sh
ENTRYPOINT [ "bash", "launch.sh" ]
