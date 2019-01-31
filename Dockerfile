FROM alpine:3.8 AS base

# Install python and modules that can't be installed via pip
# Delete the uncompiled variants to shave off ~10MB of the docker file
RUN addgroup -S -g 9898 pypiserver \
    && adduser -S -u 9898 -G pypiserver pypiserver \
    && mkdir -p /data/packages \
    && chown -R pypiserver:pypiserver /data/packages \
    # Set the setgid bit so anything added here gets associated with the
    # pypiserver group
    && chmod g+s /data/packages \
    && apk --no-cache add python py2-bcrypt py2-cffi py2-six \
    && find /usr -name "*.py" ! -name "__*" -exec rm {} \;

FROM base as builder

# Copy the requirements and install them
# Do this in a separate image in a separate directory
# to not have all the pip stuff in the final image
COPY docker-requirements.txt /requirements.txt

# Install python packages
RUN apk add --no-cache py2-pip \
    && mkdir /install \
    && pip install --prefix=/install --requirement /requirements.txt \
    && find /install -name "*.py" ! -name "__*" -exec rm {} \;

FROM base

# Copy the libraries installed via pip
COPY --from=builder /install /usr

COPY . /code

RUN apk add py2-setuptools \
    && cd code \
    && python setup.py install \
    && cd / \
    && rm -rf code

VOLUME /data/packages
USER pypiserver
WORKDIR /data
EXPOSE 8080

ENTRYPOINT ["pypi-server", "-p", "8080"]
CMD ["packages"]
