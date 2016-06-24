import boto.sdb
from boto.exception import SDBResponseError
from itertools import islice
import settings
import logging

logger = logging.getLogger('ecs_id_mapper')

conn = boto.sdb.connect_to_region(settings.simpledb_aws_region,
                                  aws_access_key_id=settings.aws_id,
                                  aws_secret_access_key=settings.aws_secret_key)

# maintain state of existing domain objects
domains = {}


def _get_domain(domain):
    """
    Check if I have the domain object in local state, if not create one, and if the domain does
    not exist, make a create_domain call and return the domain obj.
    :param domain: str. name of the domain to get
    :return: domain obj.
    """
    assert type(domain) == str
    try:
        _dom = domains[domain]
    except KeyError:
        try:
            _dom = conn.get_domain(domain)
        except SDBResponseError as e:
            if str(e.error_code) == 'NoSuchDomain':
                logger.info('Domain {dom} does not exist, creating...'.format(dom=domain))
                # The domain doesn't exist
                # create the domain
                conn.create_domain(domain)
                # get the domain object
                _dom = conn.get_domain(domain)
                # store domain obj for later use
                domains[domain] = _dom
            else:
                # something else happened that we don't know how to handle
                raise
    # finally, return domain
    return _dom


def _batch_items(items, increment=25):
    """
    generator that returns a dictionary of a specified size of keys
    :param items: dict. dictionary to batch
    :param increment: int. qty of keys per batch
    :return: dict. batched results
    """
    assert type(items) == dict
    assert type(increment) == int
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
    dom = _get_domain(domain)
    return dom.put_attributes(key, value, replace=replace)


def batch_put(items, domain):
    dom = _get_domain(domain)
    for items in _batch_items(items):
        dom.batch_put_attributes(items)
    return True


def get(key, domain, consistent_read=True):
    dom = _get_domain(domain)
    return dom.get_item(key, consistent_read=consistent_read)


def get_all_dom(domain):
    dom = _get_domain(domain)
    return dom.select('select * from `{dom}`'.format(dom=domain))


def search_domain(query, domain):
    dom =_get_domain(domain)
    return dom.select(query)


def del_key(key, domain):
    dom = _get_domain(domain)
    return dom.delete_item(get(key, domain))


def list_domains():
    return conn.get_all_domains()


def create_domain(domain):
    return conn.create_domain(domain)

