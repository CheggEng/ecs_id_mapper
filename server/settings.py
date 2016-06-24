from os import getenv
import hvac
import logging

vault_client = {}
logger = logging.getLogger('ecs_id_mapper')

vault_host = getenv('vault_host')
vault_token = getenv('vault_token')
vault_key_aws_id = getenv('vault_key_aws_id')
vault_key_aws_secret_key = getenv('vault_key_aws_secret_key')
simpledb_aws_region = getenv('simpledb_aws_region', 'us-west-2')
graylog_fqdn = getenv('graylog_fqdn')
cadvisor_port = getenv('cadvisor_port')
new_relic_account_id = getenv('new_relic_account_id')
graylog_url = getenv('graylog_url',
                     "http://{graylog_fqdn}/search?rangetype=relative&fields=message%2Csource&width=1639&relative=86400&q=tag%3Adocker.{container_id}#fields=log")
log_level = getenv('log_level', 'INFO')
server_port = getenv('server_port', 5001)
dev_mode = getenv('dev_mode', 'false')
hash_schema = 'ecs_id_mapper_hash'
events_schema = 'ecs_id_mapper_events'
services_schema = 'ecs_id_mapper_services'
new_relic_app_instance_url = "https://rpm.newrelic.com/accounts/{account_id}/applications/" \
                             "{application_id}_i{application_instance_id}"


def vault_get(name):
    try:
        client = vault_client['client']
    except KeyError:
        print("Making connection to vault host: {}".format(vault_host))
        vault_client['client'] = hvac.Client(url=vault_host, token=vault_token)
        client = vault_client['client']

    result = client.read('secret/{}'.format(name))
    if result is None:
        raise Exception('Unable to find secret {}'.format(name))
    else:
        try:
            logger.info("Retrieved secret from Vault using key {}".format(name))
            return result['data']['value']
        except KeyError:
            logger.error('Unable to find key in response data from Vault')
            raise Exception('Unable to find key in response data from Vault')

if not dev_mode == 'true':
    if not vault_token or not vault_host:
        raise Exception('Missing required config values: vault_host, vault_token')
    aws_id = vault_get(vault_key_aws_id)
    aws_secret_key = vault_get(vault_key_aws_secret_key)
    nr_api_key = vault_get('new_relic_api_key')
else:
    aws_id = getenv('aws_id')
    aws_secret_key = getenv('aws_secret_key')
    nr_api_key = getenv('nr_api_key')
