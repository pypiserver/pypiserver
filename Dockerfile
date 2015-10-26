FROM python:3.4

# Build
COPY . /code
WORKDIR /code
RUN python setup.py install
RUN pip install passlib
WORKDIR /
RUN rm -rf /pypiserver

# Data Directory
RUN mkdir -p /data/packages
WORKDIR /data

ENTRYPOINT ["pypi-server"]
CMD ["-p", "80", "packages"]
EXPOSE 80
