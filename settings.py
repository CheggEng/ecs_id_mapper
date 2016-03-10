from os import environ


vault_host = environ.get('vault_host')
vault_token = environ.get('vault_token')
graylog_fqdn = environ.get('graylog_fqdn')
cadvisor_port = environ.get('cadvisor_port')
new_relic_account_id = environ.get('new_relic_account_id')
new_relic_app_url = "https://rpm.newrelic.com/accounts/{account_id}/applications/{application_id}"
graylog_url = "http://{graylog_fqdn}/search?rangetype=relative&fields=message%2Csource&width=1639&relative=604800&q=tag%3Adocker.{container_id}#fields=log"
