FROM alpine:3.3
RUN apk add --update python
RUN apk add --update --virtual build-dependencies \
    python-dev \
    py-pip \
    && pip install requests==2.9.1 \
    && pip install docker-py==1.8.0 \
    && apk del build-dependencies
ADD . /src/
ENV sleep_interval 20
ENV log_level INFO
CMD python /src/agent.py --server_endpoint $endpoint --sleep_interval $sleep_interval --log_level $log_level