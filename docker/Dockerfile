ARG PYTHON_VERSION="3.10"

FROM python:$PYTHON_VERSION-alpine

ARG USER_UID=20000
RUN adduser -h /home/python -D -u $USER_UID python

WORKDIR /home/python

# Only copy in dependency files first, then copy in the remainder
# of the source
COPY requirements.txt /tmp
COPY requirements_dev.txt /tmp
COPY docs/requirements_docs.txt /tmp
RUN pip install --no-cache-dir \
        -r /tmp/requirements.txt \
        -r /tmp/requirements_dev.txt \
        -r /tmp/requirements_docs.txt && \
    rm /tmp/requirements*.txt

RUN mkdir -p workspace && \
    chown -R $USER_UID:$USER_UID ./workspace
COPY --chown=$USER_UID . ./workspace

USER python
RUN mkdir -p .cache/pycache
ENV PYTHONPYCACHEPREFIX=/home/python/.cache/pycache

WORKDIR /home/python/workspace
CMD [ "pytest" ]
