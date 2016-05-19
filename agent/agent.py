import requests
import logging
import time
import hashlib
import copy
from os import path, getenv
import json
from socket import gethostname
from sys import exit
import subprocess
from docker import Client


class ECSIDMapAgent():
    def __init__(self, server_endpoint, log_level):
        self.id_map = {}
        self.new_id_map = {}
        self.server_endpoint = server_endpoint
        self.logger = self._setup_logger(log_level)
        self.backoff_time = 2
        self.current_backoff_time = self.backoff_time
        self.current_retry = 0
        self.max_retries = 2
        self.hostname = gethostname()
        self.instance_ip = self.get_instance_metadata('local-ipv4')  # set these at object constr. as they don't change
        self.instance_id = self.get_instance_metadata('instance-id')
        self.instance_type = self.get_instance_metadata('instance-type')
        self.instance_az = self.get_instance_metadata('placement/availability-zone')
        self.docker_client = Client(base_url='unix://var/run/docker.sock', version='1.21')

    @staticmethod
    def _setup_logger(log_level):
        logger = logging.getLogger('ecs_id_mapper_agent')
        logger.setLevel(log_level.upper())
        logger.propagate = False
        stderr_logs = logging.StreamHandler()
        stderr_logs.setLevel(getattr(logging, log_level))
        stderr_logs.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(stderr_logs)
        return logger

    def _retry(self):
        self.logger.debug('backoff: {} retry: {} max_retry {}'.format(self.current_backoff_time,
                                                                      self.current_retry, self.max_retries))
        if self.current_retry >= self.max_retries:
            self.logger.info('Max _retry reached. Aborting')
            self.current_retry = 0
            self.current_backoff_time = self.backoff_time
            return False
        else:
            self.current_retry += 1
            self.logger.info('Sleeping for {} seconds'.format(str(self.current_backoff_time)))
            time.sleep(self.current_backoff_time)
            self.current_backoff_time **= 2
            return True

    def _http_connect(self, url, timeout=1):
        self.logger.debug('Making connection to: {}'.format(url))
        while True:
            try:
                r = requests.get(url, timeout=timeout)
                return r
            except requests.exceptions.ConnectionError:
                self.logger.error('Connection error accessing URL {}'.format(str(url)))
                if not self._retry():
                    return None
            except requests.exceptions.Timeout:
                self.logger.error(
                    'Connection timeout accessing URL {}. Current timeout value {}'.format(url, str(timeout)))
                if not self._retry():
                    return None

    def get_instance_metadata(self, path):
        self.logger.info('Checking instance metadata for {}'.format(path))
        metadata = self._http_connect('http://169.254.169.254/latest/meta-data/{}'.format(path))
        if metadata:
            return metadata.text
        else:
            return ""

    @staticmethod
    def get_container_ports(container_id):
        try:
            cmd = ["/usr/bin/docker", "port", container_id[:12]]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, errors = p.communicate()
            if errors or len(output) < 1:
                return "0", "0"
            cport, hport = output.split("-")
            cport = cport.split('/')[0]
            hport = hport.split(':')[1].strip()
            return cport, hport
        except (OSError, ValueError):
            return "0", "0"

    def get_ecs_agent_tasks(self):
        self.logger.info('Requesting data from ECS agent')
        ecs_agent_tasks_response = self._http_connect('http://127.0.0.1:51678/v1/tasks')
        ecs_agent_metadata_response = self._http_connect('http://127.0.0.1:51678/v1/metadata')

        if ecs_agent_tasks_response and ecs_agent_metadata_response:
            ecs_agent_tasks = ecs_agent_tasks_response.json()
            ecs_agent_metadata = ecs_agent_metadata_response.json()
        else:
            ecs_agent_tasks = None
            ecs_agent_metadata = None
            return False
        id_map = {}
        cluster_name = ecs_agent_metadata['Cluster']
        ecs_agent_version = ecs_agent_metadata['Version']
        for task in ecs_agent_tasks['Tasks']:
            task_id = str(task['Arn'].split(":")[-1][5:])
            desired_status = str(task['DesiredStatus'])
            known_status = str(task['KnownStatus'])
            task_name = str(task['Family'])
            task_version = str(task['Version'])
            for container in task['Containers']:
                docker_id = str(container['DockerId'])
                if desired_status == "RUNNING":
                    container_port, instance_port = self.get_container_ports(docker_id)
                else:
                    container_port, instance_port = "0", "0"
                container_name = str(container['Name'])
                pkey = hashlib.sha256()
                pkey.update(docker_id)
                pkey.update(task_id)
                pkey.update(desired_status)
                id_map[pkey.hexdigest()] = {'container_id': docker_id,
                                            'container_name': container_name,
                                            'container_port': container_port,
                                            'task_id': task_id,
                                            'task_name': task_name,
                                            'task_version': task_version,
                                            'instance_port': instance_port,
                                            'instance_ip': self.instance_ip,
                                            'instance_id': self.instance_id,
                                            'instance_type': self.instance_type,
                                            'instance_az': self.instance_az,
                                            'desired_status': desired_status,
                                            'known_status': known_status,
                                            'host_name': self.hostname,
                                            'cluster_name': cluster_name,
                                            'ecs_agent_version': ecs_agent_version,
                                            'sample_time': time.time()}
        # Update internal state
        self.new_id_map = copy.deepcopy(id_map)

    def report_event(self, event_id, action):
        for id in event_id:
            self.logger.info('Reporting new container event. Action {}. Event id: {}'.format(action, id))
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            while True:
                try:
                    r = requests.post(path.join(self.server_endpoint, 'report/event'),
                                      headers=headers,
                                      data=json.dumps({'event_id': id, 'event': action, 'timestamp': time.time()}))
                    self.logger.debug("HTTP response: " + str(r.status_code))
                    break
                except requests.exceptions.ConnectionError:
                    self.logger.info('Unable to connect to server endpoint. Sleeping for {} seconds'.format(
                        str(self.current_backoff_time)))
                    if not self._retry():
                        break

    def report_map(self):
        self.logger.info('Reporting current id map')
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        while True:
            try:
                r = requests.post(path.join(self.server_endpoint, 'report/map'),
                                  headers=headers, data=json.dumps(self.id_map))
                self.logger.debug("HTTP response: " + str(r.status_code))
                break
            except requests.exceptions.ConnectionError:
                self.logger.info('Unable to connect to server endpoint. Sleeping for {} seconds'.format(
                    str(self.current_backoff_time)))
                if not self._retry():
                    break

    def compare_hash(self):
        self.logger.info('Comparing known state to current state')
        containers_added = set(self.new_id_map.keys()) - set(self.id_map.keys())
        containers_removed = set(self.id_map.keys()) - set(self.new_id_map.keys())
        if len(containers_added) > 0:
            self.logger.info('Containers added {}'.format(containers_added))
            self.report_event(containers_added, 'added')
        if len(containers_removed) > 0:
            self.logger.info('Containers removed {}'.format(containers_removed))
            self.report_event(containers_removed, 'removed')
        if len(containers_removed) > 0 or len(containers_added) > 0:
            self.id_map = copy.deepcopy(self.new_id_map)
            self.report_map()
        else:
            self.logger.info('No container actions to report')

    def run(self):
        """
        Blocking method to run agent
        :return:
        """
        self.logger.info('Starting agent')
        for event in self.docker_client.events(decode=True):
            self.logger.debug(str(event))
            if event['status'] == 'start' or event['status'] == 'die':
                agent.get_ecs_agent_tasks()
                agent.compare_hash()


if __name__ == '__main__':
    server_endpoint = getenv('endpoint', None)
    log_level = getenv('log_level', 'INFO')

    if not server_endpoint:
        print "Error: you must specify server endpoint as EVAR 'endpoint'"
        exit(1)

    agent = ECSIDMapAgent(server_endpoint, log_level)

    # Reduce verbosity of requests logging
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Start the agent
    agent.run()
