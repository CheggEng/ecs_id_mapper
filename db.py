import boto.sdb
from boto.exception import SDBResponseError
import secrets


aws_id = secrets.get('guardian_aws_id')
aws_secret_key = secrets.get('guardian_aws_secret_key')
aws_region = secrets.get('aws_region')
conn = boto.sdb.connect_to_region(aws_region, aws_access_key_id=aws_id, aws_secret_access_key=aws_secret_key)


def put(key, value, domain):
    try:
        dom = conn.get_domain(domain)
    except SDBResponseError:
        conn.create_domain(domain)
        dom = conn.get_domain(domain)
    dom.put_attributes(key, value)


def get(key, domain, consistent_read=True):
    dom = conn.get_domain(domain)
    return dom.get_item(key, consistent_read=consistent_read)


def get_all_dom(domain):
    dom = conn.get_domain(domain)
    return dom.select('select * from `{dom}`'.format(dom=domain))


def search_domain(query, domain):
    dom = conn.get_domain(domain)
    return dom.select(query)


def list_domains():
    return conn.get_all_domains()