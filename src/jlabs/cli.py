"""Usage: jlabs [--version] [-h | --help]"""

from docopt import docopt
import logging
from jlabs import controller, utils
logger = logging.getLogger(__name__)


def run():
    args = docopt(__doc__, version="0.0.0")
    utils.setup_environment()
    logger.info("Starting jlabs")
    logger.debug(f"Arguments passed in:\n{args}")
    controller.main_menu()

