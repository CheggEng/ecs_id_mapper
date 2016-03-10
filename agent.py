import requests
import logging
import time
import hashlib
import copy
from os import path
import json
from socket import gethostname


class ECSIDMapAgent():
    def __init__(self, server_endpoint):
        self.id_map = {}
        self.new_id_map = {}
        self.server_endpoint = server_endpoint
        self.logging = logging.getLogger(__name__)
        self.backoff_time = 2
        self.current_backoff_time = self.backoff_time
        self.current_retry = 0
        self.max_retries = 2
        self.hostname = gethostname()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    def retry(self):
        self.logging.debug(self.current_backoff_time,  self.current_retry, self.max_retries)
        if self.current_retry > self.max_retries:
            self.logging.info('Max retry reached. Aborting')
            self.current_retry = 0
            self.current_backoff_time = self.backoff_time
            return False
        else:
            self.current_retry += 1
            time.sleep(self.current_backoff_time)
            self.current_backoff_time = self.current_backoff_time ** 2
            return True

    def get_instance_metadata(self, path):
        try:
            return str(requests.get('http://169.254.169.254/latest/meta-data/{}'.format(path)).text)
        except requests.exceptions.ConnectionError:
            logging.info('unable to get instance metadata for {}'.format(path))
            pass

    def get_ecs_agent_tasks(self):
        while True:
            try:
                self.logging.info('Requesting task data from ECS agent')
                r = requests.get('http://127.0.0.1:51678/v1/tasks').json()
                break
            except requests.exceptions.ConnectionError:
                self.logging.info('Unable to connect to ECS agent. Sleeping for {} seconds'.format(str(self.current_backoff_time)))
                if not self.retry():
                    break
        id_map = {}
        for task in r['Tasks']:
            task_id = str(task['Arn'].split(":")[-1][5:])
            desired_status = str(task['DesiredStatus'])
            known_status = str(task['KnownStatus'])
            task_name = str(task['Family'])
            task_version = str(task['Version'])
            instance_ip = self.get_instance_metadata('local-ipv4')
            instance_id = self.get_instance_metadata('instance-id')
            instance_type = self.get_instance_metadata('instance-type')
            for container in task['Containers']:
                docker_id = str(container['DockerId'])
                container_name = str(container['Name'])
                pkey = hashlib.sha256()
                pkey.update(docker_id)
                pkey.update(task_id)
                pkey.update(desired_status)
                id_map[pkey.hexdigest()] = {'container_id': docker_id,
                                            'container_name': container_name,
                                            'task_id': task_id,
                                            'task_name': task_name,
                                            'task_version': task_version,
                                            'instance_ip': instance_ip,
                                            'instance_id': instance_id,
                                            'instance_type': instance_type,
                                            'desired_status': desired_status,
                                            'known_status': known_status,
                                            'host_name': self.hostname,
                                            'sample_time': time.time()}
        self.new_id_map = copy.deepcopy(id_map)

    def report_event(self, event_id, action):
        for id in event_id:
            self.logging.info('Reporting new container event. Action {}. Event id: {}'.format(action, id))
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            while True:
                try:
                    r = requests.post(path.join(self.server_endpoint, 'report/event'),
                                      headers=headers,
                                      data=json.dumps({'event_id': id, 'event': action, 'timestamp': time.time()}))
                    self.logging.debug(r.text)
                    break
                except requests.exceptions.ConnectionError:
                    self.logging.info('Unable to connect to server endpoint. Sleeping for {} seconds'.format(
                    str(self.current_backoff_time)))
                    if not self.retry():
                        break

    def report_map(self):
        self.logging.info('Reporting current id map')
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        while True:
            try:
                r = requests.post(path.join(self.server_endpoint, 'report/map'),
                                  headers=headers, data=json.dumps(self.id_map))
                self.logging.debug(r.text)
                break
            except requests.exceptions.ConnectionError:
                self.logging.info('Unable to connect to server endpoint. Sleeping for {} seconds'.format(str(self.current_backoff_time)))
                if not self.retry():
                    break

    def compare_hash(self):
        self.logging.info('Comparing known state to current state')
        containers_added = set(self.new_id_map.keys()) - set(self.id_map.keys())
        containers_removed = set(self.id_map.keys()) - set(self.new_id_map.keys())
        if len(containers_added) > 0:
            self.logging.info('Containers added {}'.format(containers_added))
            self.report_event(containers_added, 'added')
        if len(containers_removed) > 0:
            self.logging.info('Containers removed {}'.format(containers_removed))
            self.report_event(containers_removed, 'removed')
        if len(containers_removed) > 0 or len(containers_added) > 0:
            self.id_map = copy.deepcopy(self.new_id_map)
            self.report_map()
        else:
            self.logging.info('No container actions to report')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--server_endpoint', required=True)
    parser.add_argument('--sleep_interval', required=False, default=20, type=int)
    args = parser.parse_args()
    agent = ECSIDMapAgent(args.server_endpoint)

    # Reduce verbosity of requests logging
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    while True:
        agent.get_ecs_agent_tasks()
        agent.compare_hash()
        time.sleep(args.sleep_interval)