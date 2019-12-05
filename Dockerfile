FROM python:3.6-alpine3.10 as base

# Copy the requirements & code and install them
# Do this in a separate image in a separate directory
# to not have all the build stuff in the final image
FROM base AS builder
RUN apk update
# Needed to build cffi
RUN apk add python-dev build-base libffi-dev
COPY . /code
RUN mkdir /install
RUN pip install --no-warn-script-location \
                --prefix=/install \
                /code --requirement /code/docker-requirements.txt

FROM base

RUN addgroup -S -g 9898 pypiserver \
    && adduser -S -u 9898 -G pypiserver pypiserver \
    && mkdir -p /data/packages \
    && chown -R pypiserver:pypiserver /data/packages \
    # Set the setgid bit so anything added here gets associated with the
    # pypiserver group
    && chmod g+s /data/packages

# Copy the libraries installed via pip
COPY --from=builder /install /usr/local
USER pypiserver
VOLUME /data/packages
WORKDIR /data
EXPOSE 8080
ENTRYPOINT ["pypi-server", "-p", "8080"]
CMD ["packages"]
