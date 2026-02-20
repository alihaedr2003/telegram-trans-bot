import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def example_function(arg1, arg2):
    try:
        logger.debug('Starting example_function with args: %s, %s', arg1, arg2)
        # Function logic here
        result = arg1 + arg2  # Example operation
        logger.debug('Result of example_function: %s', result)
        return result
    except Exception as e:
        logger.error('Error in example_function: %s', e)
        raise


def another_function(arg):
    try:
        logger.debug('Starting another_function with arg: %s', arg)
        # Function logic here
        logger.debug('Completed another_function successfully')
    except Exception as e:
        logger.error('Error in another_function: %s', e)
        raise

# Add more functions as needed with similar logging patterns
