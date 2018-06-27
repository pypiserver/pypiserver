FROM python:3.6-alpine

# Build
COPY . /code
WORKDIR /code

RUN adduser -S -u 9898 pypiserver && \
    addgroup -S -g 9898 pypiserver && \
    python setup.py install && \
    pip install passlib && \
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
