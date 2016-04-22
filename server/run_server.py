from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from server import ecs_id_mapper
import logging
import settings

logger = logging.getLogger('ecs_id_mapper')
logger.setLevel(settings.log_level)
logger.propagate = False
stderr_logs = logging.StreamHandler()
stderr_logs.setLevel(getattr(logging, settings.log_level))
stderr_logs.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(stderr_logs)

# Reduce verbosity of requests logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger.info('Starting server on port {}'.format(str(settings.server_port)))
http_server = HTTPServer(WSGIContainer(ecs_id_mapper))
http_server.listen(settings.server_port)
IOLoop.instance().start()
