from flask import Flask, request, redirect, jsonify, abort
import db
import logging
import copy
import settings

ecs_id_mapper = Flask(__name__)
logging.getLogger(__name__)


@ecs_id_mapper.route('/report/event', methods=['POST'])
def report_event():
    """
    update DB with new container task state change event
    :return:
    """
    if not request.json:
        logging.error('received non-json data')
        abort(400)
    logging.info('Received event {}'.format(request.json))
    event_id = request.json['event_id']
    event = request.json['event']
    timestamp = request.json['timestamp']
    db.put(event_id, {'event': event, 'timestamp': timestamp}, 'ecs_id_mapper_events')
    return 'true'


@ecs_id_mapper.route('/report/map', methods=['POST'])
def report_map():
    """
    update DB with new version of a container instance's id map
    :return:
    """
    if not request.json:
        logging.error('received non-json data')
        abort(400)
    logging.info('Received map update {}'.format(request.json))
    _map = request.json

    for k,v in _map.iteritems():
        container_attributes = copy.deepcopy(v)
        try:
            container_attributes['cadvisor_url'] = \
                "http://{}:9070/docker/{}".format(
                container_attributes['instance_ip'],
                container_attributes['container_id'])
            container_attributes['graylog_url'] = \
                settings.graylog_url.format(graylog_fqdn=settings.graylog_fqdn,
                                            container_id=container_attributes['container_id'][:12])
        except KeyError as e:
            logging.error('Unable to find keys in response: {}'.format(e))
        _map[k] = container_attributes
    db.batch_put(_map, 'ecs_id_mapper_hash')
    return 'true'


@ecs_id_mapper.route('/query/container_id/<container_id>', methods=['GET'])
def get_container_by_container_id(container_id):
    """
    lookup task id based on matching container id
    :param container_id: str. container id
    :return: str. task id
    """
    resultset = db.search_domain(
            'select * from `ecs_id_mapper_hash` where container_id="{container_id}" and desired_status="RUNNING"'.
                format(container_id=container_id), 'ecs_id_mapper_hash')
    try:
        return resultset.next()['task_id']
    except StopIteration:
        abort(404)


@ecs_id_mapper.route('/query/container_id/<container_id>/_all', methods=['GET'])
def get_all_container_attributes_by_container_id(container_id):
    """
    lookup all attributes a container has by its container id
    :param container_id: str. container_id
    :return: str. json encoded
    """
    resultset = db.search_domain(
            'select * from `ecs_id_mapper_hash` where container_id="{container_id}" and desired_status="RUNNING"'.
            format(container_id=container_id), 'ecs_id_mapper_hash')
    json_results = {}
    logging.debug(resultset)
    for result in resultset:
        for k,v in result.iteritems():
            json_results[k] = v
    if len(json_results) == 0:
        abort(404)
    return jsonify(json_results)



@ecs_id_mapper.route('/query/container_id/<container_id>/cadvisor', methods=['GET'])
def get_cadvisor_url_by_container_id(container_id):
    """
    Get the cadvisor URL for a given container
    :param container_id:
    :return: str.
    """
    resultset = db.search_domain(
            'select * from `ecs_id_mapper_hash` where container_id="{container_id}" and desired_status="RUNNING"'.
            format(container_id=container_id), 'ecs_id_mapper_hash')
    try:
        d = resultset.next()
        instance_ip = d['instance_ip']
        cadvisor_url = "http://{}:{}/docker/{}".format(instance_ip, settings.cadvisor_port, container_id)
        if request.args.get('redir') and request.args.get('redir').lower() == "true":
            return redirect(cadvisor_url, 302)
        else:
            return cadvisor_url
    except StopIteration:
        abort(404)


@ecs_id_mapper.route('/query/container_id/<container_id>/urls', methods=['GET'])
def get_all_container_urls(container_id):
    resultset = db.search_domain(
            'select cadvisor_url from `ecs_id_mapper_hash` where container_id="{container_id}" and desired_status="RUNNING"'.
            format(container_id=container_id), 'ecs_id_mapper_hash')
    json_results = {}
    logging.debug(resultset)
    for result in resultset:
        for k,v in result.iteritems():
            json_results[k] = v
    return jsonify(json_results)


@ecs_id_mapper.route('/query/task_id/<task_id>', methods=['GET'])
def get_container_by_task_id(task_id):
    """
    lookup container id based on matching task id
    :param task_id: str. task id
    :return: str. container id
    """
    resultset = db.search_domain(
        'select * from `ecs_id_mapper_hash` where task_id="{task_id}" and desired_status="RUNNING"'.
        format(task_id=task_id), 'ecs_id_mapper_hash')
    try:
        return resultset.next()['container_id']
    except StopIteration:
        abort(404)


@ecs_id_mapper.route('/query/task_id/<task_id>/_all', methods=['GET'])
def get_all_container_attributes_by_task_id(task_id):
    """
    lookup all attributes a container has by its task_id
    :param task_id: str. task_id
    :return: str. json encoded
    """
    resultset = db.search_domain(
            'select * from `ecs_id_mapper_hash` where task_id="{task_id}" and desired_status="RUNNING"'.
            format(task_id=task_id), 'ecs_id_mapper_hash')
    json_results = {}
    logging.debug(resultset)
    for result in resultset:
        for k,v in result.iteritems():
            json_results[k] = v
    if len(json_results) == 0:
        abort(404)
    return jsonify(json_results)


@ecs_id_mapper.route('/query/task_id/<task_id>/cadvisor', methods=['GET'])
def get_cadvisor_url_by_task_id(task_id):
    """
    Get the cadvisor URL for a given container
    :param container_id:
    :return: str.
    """
    resultset = db.search_domain(
            'select * from `ecs_id_mapper_hash` where task_id="{task_id}" and desired_status="RUNNING"'.
            format(task_id=task_id), 'ecs_id_mapper_hash')
    try:
        d = resultset.next()
        instance_ip = d['instance_ip']
        container_id = d['container_id']
        cadvisor_url = "http://{}:{}/docker/{}".format(instance_ip, settings.cadvisor_port, container_id)
        if request.args.get('redir') and request.args.get('redir').lower() == "true":
            return redirect(cadvisor_url, 302)
        else:
            return cadvisor_url
    except StopIteration:
        abort(404)


@ecs_id_mapper.route('/health')
def check_health():
    try:
        db.list_domains()
        return 'All systems go!'
    except:
        abort(500)


if __name__ == '__main__':
    # This starts the built in flask server, not designed for production use
    logging.info('Starting server...')
    ecs_id_mapper.run(debug=False, host='0.0.0.0', port=5001)