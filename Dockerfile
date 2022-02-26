ARG basetag=base

FROM sourcecodeai/ambience:${basetag}


RUN apk add --no-cache musl-dev linux-headers

RUN mkdir "/ambience-server"
WORKDIR /ambience-server

ADD poetry.lock \
    pyproject.toml \
    start_server.sh \
    uwsgi.ini \
    /ambience-server/

ADD ambience /ambience-server/ambience

RUN poetry build -f sdist  && \
    pip install ./dist/ambience-*.tar.gz && \
    pip install uwsgi && \
    aura update && \
    chmod +x /ambience-server/start_server.sh

ENV FLASK_APP="ambience.app:app"
ENTRYPOINT []
CMD ["/ambience-server/start_server.sh"]
