import boto.sdb
from boto.exception import SDBResponseError
from itertools import islice
import settings

conn = boto.sdb.connect_to_region(settings.simpledb_aws_region,
                                  aws_access_key_id=settings.aws_id,
                                  aws_secret_access_key=settings.aws_secret_key)

# maintain state of existing domain objects
domains = {}


def _check_for_domain(domain):
    try:
        conn.get_domain(domain)
        return True
    except SDBResponseError as e:
        if str(e.error_code) == 'NoSuchDomain':
            return False
        else:
            raise


def _batch_items(items, increment=25):
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


def put(key, value, domain, replace=False):
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
    return dom.put_attributes(key, value, replace=replace)


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
    for items in _batch_items(items):
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


def create_domain(domain):
    return conn.create_domain(domain)

