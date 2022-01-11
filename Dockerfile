FROM aura-full


RUN apk add --no-cache musl-dev linux-headers

RUN mkdir "/ambience-server"
ADD poetry.lock pyproject.toml start_server.sh uwsgi.ini /ambience-server/
ADD ambience /ambience-server/ambience

WORKDIR /ambience-server

RUN source $HOME/.poetry/env && \
    poetry build -f sdist  && \
    pip install ./dist/ambience-*.tar.gz && \
    pip install uwsgi && \
    chmod +x /ambience-server/start_server.sh

ENV FLASK_APP="ambience.app:app"
ENTRYPOINT []
CMD ["/ambience-server/start_server.sh"]
