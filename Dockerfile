FROM ubuntu:14.04
MAINTAINER wjimenez@chegg.com
ENV vault_host none
ENV vault_token none
ENV graylog_fqdn none
ENV new_relic_account_id none
ENV cadvisor_port none
RUN apt-get update
RUN apt-get -y install python-setuptools build-essential
RUN apt-get -y install python-dev
RUN apt-get -y install libffi-dev
RUN apt-get -y install libssl-dev
RUN easy_install urllib3[secure]
RUN easy_install flask
RUN easy_install boto
RUN easy_install hvac
RUN easy_install tornado
RUN easy_install requests
EXPOSE 5001
ADD . /src/
CMD cd /src/ && python run_server.py