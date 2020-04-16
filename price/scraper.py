import datetime
import enum
import gzip
import price.helper
import price.pricespy
import price.userbenchmark
import time

logger = price.helper.get_logger(__name__)

"""Type of scraper. Names are upper case (i.e. price.scraper.Type.HDD.name = 'HDD') and values are lower (i.e. price.scraper.Type.CPU.value = 'cpu')"""
class Type(enum.Enum):
	CPU = 'cpu'
	HDD = 'hdd'

"""
Scraper does all the downloading (i.e. scraping), parsing, and munging.
"""
class Scraper:

	"""
	Initialise the Scraper.

	Parameters:
	- pricespy_prefix - prefix of the path to write PriceSpy HTML DOM to
	- userbenchmark_prefix - prefix of the path to write UserBenchmark HTML DOM to
	- webdriver - a webdriver.WebDriver which abstracts away the Selenium web driver
	- type - the Type, i.e. whether this a CPU or HDD scraper, defaults to Type.CPU
	"""
	def __init__(self, pricespy_prefix, userbenchmark_prefix, webdriver, type=Type.CPU):
		self.pricespy_prefix = pricespy_prefix
		self.userbenchmark_prefix = userbenchmark_prefix
		self.type = type
		if type == Type.CPU:
			self.ps = price.pricespy.PriceSpy(webdriver)
			self.ub = price.userbenchmark.UserBenchmark(webdriver)
		else:
			self.ps = price.pricespy.PriceSpyHdd(webdriver)
			self.ub = price.userbenchmark.UserBenchmarkHdd()

	"""Download PriceSpy and UserBenchmark HTML DOM and save it to '<pricespy/userbenchmark_prefox>_<page_num>.htm"""
	def download(self):
		self.all_files_downloaded = []
		time_start = time.time()
		self.all_files_downloaded.extend(self.ps.download(self.pricespy_prefix, 3))
		logger.info('PriceSpy data downloaded in {:1.0f} seconds'.format(time.time() - time_start))

		time_start = time.time()
		self.all_files_downloaded.extend(self.ub.download(self.userbenchmark_prefix, 2))
		logger.info('UserBenchmark data downloaded in {:1.0f} seconds'.format(time.time() - time_start))

	"""Frees up some processes/resources by telling Selenium to quit"""
	def quit_selenium(self):
		self.ps.quit_selenium()
		self.ub.quit_selenium()

	"""Parses PriceSpy and UserBenchmark HTML DOM and returns a dictionary {'pricespy_data': ps_data, 'userbenchmark_data': ub_data}"""
	def parse(self):
		ps_data = self.ps.parse_prefixes(self.pricespy_prefix)
		logger.info('Number of PriceSpy data rows: {}'.format(len(ps_data)))

		ub_data = self.ub.parse_prefixes(self.userbenchmark_prefix)
		logger.info('Number of UserBenchmark data rows: {}'.format(len(ub_data)))

		return {'pricespy_data': ps_data, 'userbenchmark_data': ub_data}

	"""Munge the data together writing output to 'web/price_performance_<yyyyMMdd>.json'"""
	def munge(self, ps_data, ub_data):
		m = price.munger.CpuMunger() if self.type == Type.CPU else price.munger.HddMunger()
		data = m.munge(ps_data, ub_data)
		return data

	"""
	Uploads the JSON data to S3 (will gzip too) as "<prefix>/price_performance_<data_date>.json" and also updates the latest.js file.
	Parameters:
	- s3_client - the Boto3 S3 client to use
	- bucket - name of the bucket to upload to
	- prefix - key prefix to upload the file as. Note the base file name of <data_file_path> will be used
	- json_data - the JSON data to upload
	- data_date - the date of the data. If None will use today's date
	"""
	def upload_data_to_s3(self, s3_client, bucket, prefix, json_data, data_date=None):
		compressed_data = gzip.compress(json_data.encode('utf-8'))
		file_name = 'price_performance_' + self.type.value + '_' + (data_date if data_date else datetime.date.today().strftime("%Y%m%d")) + '.json'
		key = prefix + '/' + file_name
		logger.debug('Uploading data file to S3 as ' + key)
		s3_client.put_object(Body=compressed_data, Bucket=bucket, CacheControl='max-age=31536000', ContentEncoding='gzip', ContentType='application/javascript', Key=key)

		key = prefix + '/latest_' + self.type.value + '.js'
		s3_client.put_object(Body='var LATEST_' + self.type.name + '_DATA_FILE="' + file_name + '";', Bucket=bucket, CacheControl='max-age=3600', ContentType='application/javascript', Key=key)
		logger.debug('Updated S3 index file ' + key)