import logging
import sys

def setup_logger(name, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    
    # Create handler that outputs to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    
    return logger