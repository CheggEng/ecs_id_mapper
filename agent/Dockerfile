FROM ubuntu:14.04
RUN apt-get -y install python-setuptools
RUN easy_install pip
RUN pip install requests==2.9.1
ADD . /src/
ENV sleep_interval 20
ENV log_level INFO
CMD python /src/agent.py --server_endpoint $endpoint --sleep_interval $sleep_interval --log_level $log_level