FROM python:3.6-alpine

# Build
COPY . /code
WORKDIR /code

RUN addgroup -S -g 9898 pypiserver && \
    adduser -S -u 9898 -G pypiserver pypiserver && \
    apk add --no-cache --virtual .build-deps  \
      bzip2-dev \
      coreutils \
      dpkg-dev dpkg \
      expat-dev \
      findutils \
      gcc \
      gdbm-dev \
      libc-dev \
      libffi-dev \
      libressl \
      libressl-dev \
      linux-headers \
      make \
      ncurses-dev \
      pax-utils \
      readline-dev \
      sqlite-dev \
      tcl-dev \
      tk \
      tk-dev \
      xz-dev \
      zlib-dev &&\
    python setup.py install && \
    pip install passlib bcrypt && \
    apk del .build-deps && \
    cd / && \
    rm -rf /code && \
    mkdir -p /data/packages && \
    chown -R pypiserver:pypiserver /data/packages && \
    # Set the setgid bit so anything added here gets associated with the
    # pypiserver group
    chmod g+s /data/packages

VOLUME /data/packages
USER pypiserver
WORKDIR /data
EXPOSE 8080

ENTRYPOINT ["pypi-server", "-p", "8080"]
CMD ["packages"]
