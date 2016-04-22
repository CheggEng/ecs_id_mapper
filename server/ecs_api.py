import settings
import boto3
import botocore.exceptions
import logging

logger = logging.getLogger('ecs_id_mapper')

client = boto3.client('ecs',
                      aws_access_key_id=settings.aws_id,
                      aws_secret_access_key=settings.aws_secret_key,
                      region_name=settings.simpledb_aws_region
                      )


def get_task_ids_from_service(service_name, cluster_name):
    logger.info('Making call to AWS API for service {} and cluster {}'.format(service_name, cluster_name))
    try:
        tasks = client.list_tasks(cluster=cluster_name, serviceName=service_name)['taskArns']
    except botocore.exceptions.ClientError:
        logger.info('ECS service {} not found'.format(service_name))
        raise Exception('ECS service not found')
    logger.debug(tasks)
    tlist = []
    if len(tasks) >= 1:
        for task in tasks:
            tlist.append(task.split('/')[1])
    return tlist

