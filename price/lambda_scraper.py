import boto3
import datetime
import gzip
import json
import logging
import price.helper
import price.munger
import price.scraper
import price.webdriver
import os
import random
import shutil
import string

logger = price.helper.get_logger(__name__)

def get_environ(key):
	if key in os.environ:
		return os.environ[key]
	return '<not set>'

def create_sym_link(source, target):
	if not os.path.isfile(target):
		os.symlink(source, target)

class LambdaHandler:

	def __init__(self):
		logger.debug('Initialising handler...')
		if 'DEBUG_ENABLED' in os.environ and os.environ['DEBUG_ENABLED'].lower() == 'true':
			price.helper.set_log_level(logging.DEBUG)

		if not os.path.isdir('/tmp/aws'):
			# Setup fonts into /tmp. Note this is shared between initialisations and invocations
			# TODO perhaps we setup fonts.conf to point to /opt where the Lambda layer is instead of /tmp and separate libs???
			shutil.copytree('/opt/aws', '/tmp/aws')

		# Setup libX11, glib2-2.56.1-4.amzn2.x86_64, libxcb, libXau libraries.
		# For some reason symlinks aren't setup between invocations even after deploying a new version of the Lambda code
		create_sym_link('/tmp/aws/lib/libX11-xcb.so.1.0.0', '/tmp/aws/lib/libX11-xcb.so.1')
		create_sym_link('/tmp/aws/lib/libX11.so.6.3.0', '/tmp/aws/lib/libX11.so.6')
		create_sym_link('/tmp/aws/lib/libXau.so.6.0.0', '/tmp/aws/lib/libXau.so.6')
		create_sym_link('/tmp/aws/lib/libglib-2.0.so.0.5600.1', '/tmp/aws/lib/libglib-2.0.so.0')
		create_sym_link('/tmp/aws/lib/libxcb.so.1.1.0', '/tmp/aws/lib/libxcb.so.1')

		# Setup environment variables for each initialisation
		os.environ['FONTCONFIG_PATH'] = '/tmp/aws'
		if 'LD_LIBRARY_PATH' in os.environ:
			if os.environ['LD_LIBRARY_PATH'].find('/tmp/aws/lib') < 0:
				os.environ['LD_LIBRARY_PATH'] = '/tmp/aws/lib:' + os.environ['LD_LIBRARY_PATH']
		else:
			os.environ['LD_LIBRARY_PATH'] = '/tmp/aws/lib'

		logger.debug('Initialising handler complete (FONTCONFIG_PATH=' + get_environ('FONTCONFIG_PATH') + ', LD_LIBRARY_PATH=' + get_environ('LD_LIBRARY_PATH') + ')')

	def scrape(self, event, context, type):
		logger.debug('Handling scrape request for ' + type.name + ' type...')

		uniqueifier = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(6))
		today = datetime.date.today().strftime("%Y%m%d")
		pricespy_prefix = '/tmp/pricespy_' + type.value + '_' + uniqueifier + '_' + today
		userbenchmark_prefix = '/tmp/userbenchmark_' + type.value + '_' + uniqueifier + '_' + today + ('.csv' if type.name == 'HDD' else '')
		chromedriver_log = '/tmp/chromedriver_' + type.value + '_' + uniqueifier + '.log'
		driver = price.webdriver.ChromeWebDriver('/opt/chromium/chromium', '/opt/chromedriver/chromedriver', chromedriver_log)

		try:
			scraper = price.scraper.Scraper(pricespy_prefix, userbenchmark_prefix, driver, type)
			scraper.download()
			scraper.quit_selenium()
		except:
			logger.error('Failed to scrape, collecting logs...')
			if os.path.isfile(chromedriver_log):
				with open(chromedriver_log, 'r') as f:
					logger.error('Output from ' + chromedriver_log + ' is:\n' + f.read())
			else:
				logger.error('No output from ' + chromedriver_log + '.')
			raise

		if os.environ['UPLOAD_DOM'] == 'true':
			for file_downloaded in scraper.all_files_downloaded:
				with open(file_downloaded, 'r', encoding='utf-8') as f:
					compressed_data = gzip.compress(f.read().encode('utf-8'))
					s3.put_object(Body=compressed_data, Bucket=os.environ['S3_BUCKET'], CacheControl='max-age=31536000', ContentEncoding='gzip', Key=file_downloaded[1:])
			logger.debug('Uploaded raw download files to S3: ' + str(scraper.all_files_downloaded))

		data = scraper.parse()
		data = scraper.munge(data['pricespy_data'], data['userbenchmark_data'])
		logger.debug('Munge complete. #Combined={0}, #OrphanPrice={1}, #OrphanPerformance={2}'.format(len(data['data']), len(data['orphan_price_data']), len(data['orphan_perf_data'])))
		logger.debug(price.munger.format(data))

		scraper.upload_data_to_s3(s3, os.environ['S3_BUCKET'], os.environ['S3_KEY_PREFIX'], json.dumps(data['data']), today)
		logger.debug('Uploading to S3 complete')

s3 = boto3.client('s3', region_name=os.environ['S3_REGION'])

lambda_handler = LambdaHandler()

def handler(event, context):
	if 'driver' in event:
		# Print temp directory
		#for root, dirs, files in os.walk('/tmp/aws/'):
		#	print('root: ' + str(root) + ', dirs: ' + str(dirs) + ', files: ' + str(files))
		
		# Launch Chrome driver
		#print(str(os.system('/opt/chromedriver/chromedriver')))

		# Print Chrome browser verison
		driver = price.webdriver.ChromeWebDriver('/opt/chromium/chromium', '/opt/chromedriver/chromedriver', '/tmp/chromedriver.log').getWebDriver()
		print(f'Chrome browser version: {driver.capabilities["browserVersion"]}')
	elif 'scrape' in event:
		lambda_handler.scrape(event, context, price.scraper.Type.CPU)
		lambda_handler.scrape(event, context, price.scraper.Type.HDD)