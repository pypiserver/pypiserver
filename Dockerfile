FROM python:3.8-alpine3.12 as base

# Copy the requirements & code and install them
# Do this in a separate image in a separate directory
# to not have all the build stuff in the final image
FROM base AS builder_gosu

ENV GOSU_VERSION 1.12

RUN apk add --no-cache --virtual .build-deps \
        ca-certificates \
        dpkg \
        gnupg \
    && dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')" \
    && wget -O /usr/local/bin/gosu https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-${dpkgArch} \
    && wget -O /usr/local/bin/gosu.asc https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-${dpkgArch}.asc \
    # verify the signature
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu \
    && command -v gpgconf && gpgconf --kill all || true \
    && rm -rf "$GNUPGHOME" /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    # check installation
    && gosu --version \
    && gosu nobody true \
    && apk del --no-cache \
        .build-deps \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/*

FROM base AS builder_dependencies

WORKDIR /code

COPY docker/docker-requirements.txt .

# Install requirements
RUN apk add --no-cache --virtual .build-deps \
        build-base \
        libffi-dev \
    && mkdir /install \
    && python -m pip install \
        --no-warn-script-location \
        --prefix=/install \
        --requirement docker-requirements.txt

# Install pypiserver
# - do this separately from deps so that when developing, every change does not
#   require reinstalling deps
COPY pypiserver pypiserver
COPY setup.cfg .
COPY setup.py .
COPY README.rst .
RUN python -m pip install --no-warn-script-location --prefix=/install .

FROM base

WORKDIR /data
# Copy the libraries installed via pip
COPY --from=builder_dependencies /install /usr/local
COPY --from=builder_gosu /usr/local/bin/gosu /usr/local/bin/gosu
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/gunicorn.conf.py /data

# Use a consistent user and group ID so that linux users
# can create a corresponding system user and set permissions
# if desired.
RUN apk add bash \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/* \
    && addgroup -S -g 9898 pypiserver \
    && adduser -S -u 9898 -G pypiserver pypiserver --home /data\
    && mkdir -p /data/packages \
    && chmod +x /entrypoint.sh 

VOLUME /data/packages
ENV PYPISERVER_PORT=8080
# PORT is deprecated. Please use PYPISERVER_PORT instead
ENV PORT=$PYPISERVER_PORT
# Flush logs immediately to stdout
ENV PYTHONUNBUFFERED=t
EXPOSE $PYPISERVER_PORT

ENTRYPOINT ["/entrypoint.sh"]
