import hvac
import settings
import logging

# setup client interface to Vault
vault_host = settings.vault_host
logger = logging.getLogger(__name__)
logger.info("Making connection to vault host: {}".format(vault_host))
client = hvac.Client(url=vault_host, token=settings.vault_token)


def get(name):
    result = client.read('secret/{}'.format(name))
    if result is None:
        raise Exception('Unable to find secret {}'.format(name))
    else:
        try:
            logger.info("Retrieved secret from Vault using key {}".format(name))
            return result['data']['value']
        except KeyError:
            raise Exception('Unable to find key in response data from Vault')
