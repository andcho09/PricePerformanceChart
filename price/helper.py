import boto3
import configparser
import logging
import os

"""Utility functions"""

DEFAULT_LOG_LEVEL = None
LOGGERS = []

"""
Returns a new logger for the given name. Parameters:
- name - the name of the logger
- steram - where to stream output, e.g. sys.stdout. Defaults to None. Setting this will call logging.basicConfig(...) affecting all subsequent loggers.
Returns: A new logger, default level is INFO
"""
def get_logger(name, stream=None):
	global DEFAULT_LOG_LEVEL
	global LOGGERS
	if DEFAULT_LOG_LEVEL is None:
		DEFAULT_LOG_LEVEL = logging.INFO
	if stream is not None:
		logging.basicConfig(stream=stream)
	logger = logging.getLogger(__name__)
	logger.setLevel(DEFAULT_LOG_LEVEL)
	LOGGERS.append(logger)
	return logger

"""Changes the log level for all future and previously created loggers"""
def set_log_level(level):
	global DEFAULT_LOG_LEVEL
	global LOGGERS
	DEFAULT_LOG_LEVEL = level
	for logger in LOGGERS:
		logger.setLevel(DEFAULT_LOG_LEVEL)

"""Encapsulate S3 client and details"""
class S3:

	"""This is not intended to be invoked directly, use the 'get__S3_DETAILS' function instead"""
	def __init__(self, region, bucket, key_prefix):
		self.client = boto3.client('s3', region_name=region) # bot3 s3 client
		self.bucket = bucket # the bucket we should be using
		self.key_prefix = key_prefix # key prefix to use when uploading files

_S3_DETAILS = None

"""Lazily retrieve S3 client and details from environment variables"""
def get_s3_details():
	global _S3_DETAILS
	if _S3_DETAILS is None:
		_S3_DETAILS = S3(os.environ['S3_REGION'], os.environ['S3_BUCKET'], os.environ['S3_KEY_PREFIX'])
	return _S3_DETAILS

_CONFIG_READ = False

""" Initialise environment variables from the given .ini file (default is 'priceperformancechart.ini')"""
def init_environ(file='priceperformancechart.ini'):
	global _CONFIG_READ
	if _CONFIG_READ == False:
		config = configparser.ConfigParser()
		config.read(file)
		os.environ['S3_REGION'] = config['S3']['region']
		os.environ['S3_BUCKET'] = config['S3']['bucket']
		os.environ['S3_KEY_PREFIX'] = config['S3']['key_prefix']
		_CONFIG_READ = True
