import time
import db
import requests
import logging
import settings
import ecs_api

logger = logging.getLogger('ecs_id_mapper')

# Reduce verbosity of requests logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

nr_api_key = settings.nr_api_key


class NewRelicAPIException(Exception):
    '''
    Unable to get an acceptable response from New Relic API
    '''


def get_map_entries(timerange=30):
    query = "select * from `ecs_id_mapper_hash` where `newrelic_url` is null and `sample_time` between '{}' and '{}'".\
        format(time.time() - timerange, time.time())
    result = db.search_domain(query, 'ecs_id_mapper_hash')
    return result


def update_nr_URL():
    for result in get_map_entries():
        nr_url = get_new_relic_app_instance_url(result['container_id'])
        _result = result
        _result['newrelic_url'] = nr_url
        if len(nr_url) > 0 and nr_url is not 'unknown':
            logger.info('Updating record with New Relic URL')
            print(result.name, _result, 'ecs_id_mapper_hash')
            db.put(result.name, _result, 'ecs_id_mapper_hash')
        else:
            logger.info('New Relic URL not found')


def get_new_relic_app_instance_url(container_id):
    """
    Query New Relic API for list of applications filtered by host id (docker short id). If the application was found
    key 'applications' will contain a list with details about the New Relic application.
    :param container_id:
    :return:
    """
    container_id = container_id[:12]  # Slice container id to shortened form
    # NR hostnames will always be in this format
    logger.info('Making request to New Relic API for container id {}'.format(container_id))
    try:
        r = requests.get('https://api.newrelic.com/v2/applications.json?filter[host]={}'.format(container_id),
                         headers={"X-Api-Key": nr_api_key,
                                  "content-type": "application/x-www-form-urlencoded"},
                         timeout=1)
        logger.debug(r.text)
        if len(r.json()['applications']) > 1:
            # we got more applications back than we expected
            logger.info('found more than one new relic application for that container')
            raise NewRelicAPIException

        application_id = r.json()['applications'][0]['id']
        r = requests.get('https://api.newrelic.com/v2/applications/{}/hosts.json?filter[hostname]={}'.format(
            application_id, container_id),
                         headers={"X-Api-Key": nr_api_key,
                                  "content-type": "application/x-www-form-urlencoded"},
                         timeout=1)
        logger.debug(r.text)
        application_instance_id = r.json()['application_hosts'][0]['links']['application_instances'][0]
        return settings.new_relic_app_instance_url.format(account_id=settings.new_relic_account_id,
                                                          application_id=application_id,
                                                          application_instance_id=application_instance_id)
    except requests.exceptions.Timeout:
        logger.info("New Relic didn't respond in time")
        raise NewRelicAPIException
    except (IndexError, KeyError):
        logger.info("Received an invalid response from New Relic. Likely this container ID wasn't found")
        if r:
            logger.debug(r.json())
        raise NewRelicAPIException
    except requests.exceptions.SSLError as e:
        logger.error("SSL error connecting to New Relic {}".format(e))
        raise NewRelicAPIException


def get_new_relic_service_url(service_name, cluster_name):
    """
    Get the new relic application URL for a given service. Assumes any one of the tasks in service report to the same
    new relic 'app'.
    :param service_name: str. Name of the service
    :param cluster_name: str. Name of cluster service is in
    :return: str. URL of new relic page for app
    """
    try:
        task_id = ecs_api.get_task_ids_from_service(service_name,cluster_name)
    except:
        raise NewRelicAPIException
    else:
        task_id = task_id[0]  # take the first task ID we found since we only need one
    logger.info('Found task_id {} for service {}'.format(task_id, service_name))
    resultset = db.search_domain(
                'select * from `ecs_id_mapper_hash` where task_id="{task_id}" and desired_status="RUNNING"'.
                format(task_id=task_id), 'ecs_id_mapper_hash')
    try:
        r = resultset.next()
        new_relic_url = r['new_relic_url']
    except StopIteration:
        logger.info('Unable to find task {} details in our database'.format(task_id))
        raise NewRelicAPIException
    except KeyError:
        new_relic_url = get_new_relic_app_instance_url(r['container_id'])
        db.put(r.name, {"new_relic_url": new_relic_url}, settings.hash_schema, replace=True)
    return new_relic_url.split('_')[0]
