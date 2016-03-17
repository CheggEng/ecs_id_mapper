import boto.sdb
from boto.exception import SDBResponseError
import secrets
from itertools import islice

aws_id = secrets.get('guardian_aws_id')
aws_secret_key = secrets.get('guardian_aws_secret_key')
aws_region = secrets.get('aws_region')
conn = boto.sdb.connect_to_region(aws_region, aws_access_key_id=aws_id, aws_secret_access_key=aws_secret_key)

# maintain state of existing domain objects
domains = {}


def batch_items(items, increment=25):
    start = 0
    end = increment
    incr = increment
    r = {}
    while True:
        for k,v in islice(items.iteritems(), start, end):
            r[k] = v
        if len(r) > 0:
            yield r
            start = end+1
            end += incr
            r = {}
        else:
            break


def put(key, value, domain):
    try:
        dom = domains[domain]
    except KeyError:
        try:
            dom = conn.get_domain(domain)
        except SDBResponseError:
            conn.create_domain(domain)
            dom = conn.get_domain(domain)
        # store domain obj for later use
        domains[domain] = dom
    # put k,v
    return dom.put_attributes(key, value)


def batch_put(items, domain):
    try:
        dom = domains[domain]
    except KeyError:
        try:
            dom = conn.get_domain(domain)
        except SDBResponseError:
            conn.create_domain(domain)
            dom = conn.get_domain(domain)
        # store domain obj for later use
        domains[domain] = dom
    for items in batch_items(items):
        r = dom.batch_put_attributes(items)
    return True


def get(key, domain, consistent_read=True):
    try:
        dom = domains[domain]
    except KeyError:
        try:
            dom = conn.get_domain(domain)
        except SDBResponseError:
            return None
    return dom.get_item(key, consistent_read=consistent_read)


def get_all_dom(domain):
    try:
        dom = domains[domain]
    except KeyError:
        try:
            dom = conn.get_domain(domain)
        except SDBResponseError:
            return None
    return dom.select('select * from `{dom}`'.format(dom=domain))


def search_domain(query, domain):
    try:
        dom = domains[domain]
    except KeyError:
        try:
            dom = conn.get_domain(domain)
        except SDBResponseError:
            return None
    return dom.select(query)


def list_domains():
    return conn.get_all_domains()