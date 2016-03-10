import time
import db
import requests
import logging
import settings
import secrets

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Reduce verbosity of requests logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

nr_api_key = secrets.get('new_relic_api_key')


def get_map_entries(timerange=30):
    query = "select * from `ecs_id_mapper_hash` where `newrelic_url` is null and `sample_time` between '{}' and '{}'".\
        format(time.time() - timerange, time.time())
    result = db.search_domain(query, 'ecs_id_mapper_hash')
    return result


def update_nr_URL():
    for result in get_map_entries():
        nr_url = get_newrelic_url(result['container_id'])
        _result = result
        _result['newrelic_url'] = nr_url
        if len(nr_url) > 0 and nr_url is not 'unknown':
            logger.info('Updating record with New Relic URL')
            print(result.name, _result, 'ecs_id_mapper_hash')
            db.put(result.name, _result, 'ecs_id_mapper_hash')
        else:
            logger.info('New Relic URL not found')


def get_newrelic_url(container_id):
    """
    Query New Relic API for list of applications filtered by host id (docker short id). If the application was found
    key 'applications' will contain a list with details about the New Relic application.
    :param container_id:
    :return:
    """
    container_id = container_id[:12]
    try:
        r = requests.get('https://api.newrelic.com/v2/applications.json',
                         headers={"X-Api-Key": nr_api_key,
                                  "content-type": "application/x-www-form-urlencoded"},
                         data="filter[host]={}".format(container_id),
                         timeout=1)
        if len(r.json()['applications']) > 1:
            # we got more applications back than we expected
            logging.info('found more than one new relic application for that container')
            return "unknown"
        application_id = r.json()['applications'][0]['id']
        application_instance_id = r.json()['applications'][0]['links']['application_instances']
        return settings.new_relic_app_url.format(account_id=settings.new_relic_account_id,
                                                 application_id=application_id)
    except requests.exceptions.Timeout:
        logging.info("New Relic didn't respond in time")
        return "unknown"
    except (IndexError, KeyError):
        logging.info("Received an invalid response from New Relic. Likely this container ID wasn't found")
        if r:
            logging.debug(r.json())
        return "unknown"
    except requests.exceptions.SSLError as e:
        logging.error("SSL error connecting to New Relic {}".format(e))
        return "unknown"


def run_service():
    logger.info('Checking for New Relic URLs')
    update_nr_URL()
    logging.info('Sleeping')
    time.sleep(30)

if __name__ == '__main__':
    run_service()