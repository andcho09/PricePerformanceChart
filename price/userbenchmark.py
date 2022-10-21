import boto3
import bs4
import csv
import datetime
import gzip
import price.helper
import price.webdatasource
import price.webdriver
import requests
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

"""UserBenchmark's CPUs by fastest average effective speed"""
class UserBenchmark(price.webdatasource.WebDataSource):

	"""
	Parse UserBenchmark HTML DOM adding dictionary objects to the 'result' array. Dictionary format is:
	{'name': <name>, '1-core': <score>, '2-core': <score>, '8-core': <score>, 'avg': <score>, 'user-rating': <score>}
	"""
	def parse_soup(self, result, soup):
		product_eles = soup.find_all('tr', attrs={'class': 'hovertarget'}, limit=50)
		if len(product_eles) > 0:
			th_eles = product_eles[0].parent.parent.find_all('th')
			column_indexes = self._determine_column_indexes(th_eles)
		else:
			return
		for product_ele in product_eles:
			result.append(self._parse(product_ele, column_indexes))

	def _parse(self, product_ele, column_indexes):
		a_eles = product_ele.find_all('a')
		name_a_ele = a_eles[1]
		name = name_a_ele.previousSibling.string.strip() + ' ' + name_a_ele.string
		result = {'name': name, '1-core': None, '2-core': None, '8-core': None, 'avg': None, 'user-rating': None}

		td_eles = product_ele.find_all('td')
		for i, td_ele in enumerate(td_eles):
			if i in column_indexes:
				div_ele = td_ele.find('div')
				div_ele_contents = div_ele.contents
				if len(div_ele_contents) == 3: # Current column has up/down arrows around value
					value = div_ele_contents[1]
				elif len(div_ele_contents) == 1:
					if type(div_ele_contents[0]).__name__ == 'NavigableString': # Current column is nothing special
						value = div_ele.string
					else: # Current column value has percentile info
						value = div_ele_contents[0].contents[0]
				else:
					value = div_ele.string
				result[ column_indexes[i] ] = str(value)

		return result

	"""
	Parses the <th> elements to calculate and return indexes to concept
	"""
	def _determine_column_indexes(self, th_eles):
		index_to_concept = {}
		for i, th_ele in enumerate(th_eles):
			if 'data-mhth' in th_ele.attrs:
				concept = th_ele.attrs['data-mhth']
				if concept == 'MC_POPULARITY':
					index_to_concept[i] = 'user-rating'
				elif concept == 'MC_BENCH':
					index_to_concept[i] = 'avg'
				elif concept == 'MCCPU_1CA':
					index_to_concept[i] = '1-core'
				elif concept == 'MCCPU_2CA':
					index_to_concept[i] = '2-core'
				elif concept == 'MCCPU_8CA':
					index_to_concept[i] = '8-core'
		return index_to_concept

	def download(self, output_file_name_prefix, num_pages=1):
		self.files_downloaded = []
		self.output_file_name_prefix = output_file_name_prefix
		self.current_page = 1
		self.num_pages = num_pages
		src = self._download('https://cpu.userbenchmark.com/', 'CPU UserBenchmarks - ', 'tr[class="hovertarget "]', 'body')
		file_name = output_file_name_prefix + '_1.htm'
		with open(file_name, 'w', encoding='utf-8') as f:
			f.write(src)
		self.files_downloaded.append(file_name)
		return self.files_downloaded

	def _pre_wait_navigation(self, driver):
		# Hit drop down to change sorting (default is by user rating)
		chooser_ele = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 's2id_mh-td-chooser')))
		chooser_ele.click()
		# Click 3rd option (sort by fatest average effective speed)
		option = WebDriverWait(driver, 2).until(lambda x: x.find_element(By.XPATH, '(//span[@class="select2-match"])[3]'))
		clickable_option = option.find_element(By.XPATH, './..')
		clickable_option.click()
		time.sleep(1.5) # This is gross but it's possible on Lambda for the progress bar to not have even shown up yet if this is too low
		# Wait until progress bar gone
		WebDriverWait(driver, 5).until_not(lambda x: x.find_element(By.CSS_SELECTOR, 'div[class="ajaxProgress"]').is_displayed())

		if len(driver.find_elements(By.CSS_SELECTOR, 'th.mh-td-col[data-mhth="MCCPU_1CA"]')) == 0:
			# Add 1-core pts if not there
			add_column_links = driver.find_elements(By.CSS_SELECTOR, 'th.mh-td-th-arrow[title="Add columns"] a.nodec')
			add_column_links[-1].click() # Click the last one, that should be the link to open the options panel (instead of the hidden one)
			column_dialog = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.list-group')))
			options = column_dialog.find_elements(By.TAG_NAME, 'a')
			for option in options:
				if option.text.find('1-Core') >= 0:
					option.click()
					time.sleep(1.5) # This is gross but it's possible on Lambda for the progress bar to not have even shown up yet if this is too low
					# Wait until progress bar gone
					WebDriverWait(driver, 5).until_not(lambda x: x.find_element(By.CSS_SELECTOR, 'div[class="ajaxProgress"]').is_displayed())
					break

	def _post_download(self, driver):
		for i in range(1, self.num_pages):
			next = driver.find_element(By.XPATH, '//ul[@class="pagination pagination-lg"]/li[2]/a') # Next page
			driver.execute_script('arguments[0].scrollIntoView(false);', next)
			next.click()
			time.sleep(1.5) # This is gross but it's possible on Lambda for the progress bar to not have even shown up yet if this is too low
			# Wait until progress bar gone
			WebDriverWait(driver, 5).until_not(lambda x: x.find_element(By.CSS_SELECTOR, 'div[class="ajaxProgress"]').is_displayed())
			body = driver.find_element(By.TAG_NAME, 'body')
			file_name = self.output_file_name_prefix + '_' + str(i + 1) + '.htm'
			with open(file_name, 'w', encoding='utf-8') as f:
				f.write(body.get_attribute('outerHTML'))
			self.files_downloaded.append(file_name)

"""
UserBenchmark's HDDs by fastest average effective speed. Note this implementation doesn't use Selenium (just downloads UserBenchmark's CSV)
so should be fast and maintains the API of price.webdatasource.WebDataSource albeit with some parameters ignored.
"""
class UserBenchmarkHdd(price.webdatasource.WebDataSource):

	EXPECTED_HEADER = 'Type,Part Number,Brand,Model,Rank,Benchmark,Samples,URL'
	S3_CACHE_KEY = 'tmp/HDD_UserBenchmarks.csv'

	"""Special constructor since this doesn't use Selenium, we don't need to pass a web driver"""
	def __init__(self):
		super().__init__(None)

	"""
	Download operates differently. It just hits UserBenchmark's CSV download (which doesn't have as much detail) and uses S3 as a cache
	under the key 'tmp/HDD_UserBenchmarks.csv' (gzipped). Locally, the file is saved to the given output_file_name (no compression)

	Parameters:
	- output_file_name - name of the file to save to local disk. No suffixes are added to this prefix (i.e. the prefix is the file name).
		Defaults to '/tmp/HDD_UserBenchmarks.csv'
	- num_pages - this is ignored
	"""
	def download(self, output_file_name='/tmp/HDD_UserBenchmarks.csv', num_pages=1):
		csv_content = None
		s3_details = price.helper.get_s3_details()
		s3_list = s3_details.client.list_objects_v2(Bucket=s3_details.bucket, Prefix=self.S3_CACHE_KEY)
		if 'Contents' in s3_list and len(s3_list['Contents']) > 0:
			last_modified = s3_list['Contents'][0]['LastModified']
			if last_modified > datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7):
				# S3 cache is fresh (within 7 days old)
				s3_resp = s3_details.client.get_object(Bucket=s3_details.bucket, Key=self.S3_CACHE_KEY)
				csv_content = gzip.decompress(s3_resp['Body'].read())

		if csv_content == None:
			# S3 cache is older than 7 days ago. Refersh it.
			userbenchmark_hdd_csv_url = 'https://www.userbenchmark.com/resources/download/csv/HDD_UserBenchmarks.csv'
			resp = requests.get(userbenchmark_hdd_csv_url)
			if resp.status_code != 200:
				raise Exception('Could not download UserBenchmark HDD CSV using url={}. Response: {}'.format(userbenchmark_hdd_csv_url, resp))
			csv_content = resp.content
			compressed_data = gzip.compress(resp.content)
			s3_details.client.put_object(Body=compressed_data, Bucket=s3_details.bucket, ContentEncoding='gzip', ContentType='text/csv', Key=self.S3_CACHE_KEY)

		with open(output_file_name, 'wb') as output_file:
			output_file.write(csv_content)
		return [output_file_name]

	"""
	Parse CSV files. Returns a list of dictionary objects in the format: {'brand': <brand>, 'mfg_code': <mfg_code>, 'model': <model>, 'avg': <score>}.
	Note there are issues with the data where empty string brand and mfg_code exist.
	"""
	def parse(self, *input_file_paths):
		result = []
		for input_file_path in input_file_paths:
			with open(input_file_path, 'r', encoding='utf-8') as f:
				self._parse(result, csv.reader(f))
		return result

	"""Parse the CSV file with the given prefix. No suffix is added so the prefix is the filename to parse."""
	def parse_prefixes(self, prefix, suffix='.htm'):
		return self.parse(prefix)

	def _parse(self, result, csv_reader):
		header = None
		for row in csv_reader:
			if header == None:
				# Assert header row is as we expect
				header = ','.join(row)
				if header != self.EXPECTED_HEADER or len(row) != 8:
					raise Exception('Something is wrong with the CSV file. Expected "{}" but got "{}"'.format(self.EXPECTED_HEADER, header))
				continue
			avg_benchmark = float(row[5].strip())
			if avg_benchmark < 42:
				continue # Skip over bottom 50% of performers, these are usually 5400 rpm drives which I don't care about
			samples = int(row[6].strip())
			if int(row[6]) < 12:
				continue # Skip over rows that have < 12 samples (i.e. skip the bottom 1% of samples)
			result.append({'brand': row[2].strip(), 'mfg_code': row[1].strip(), 'model': row[3].strip(), 'samples': samples, 'avg': row[5].strip()})

	def parse_soup(self, result, soup):
		raise NotImplementedError # This shouldn't be called as the 'parse' method above won't call this

if __name__ == '__main__':
	price.helper.init_environ()
	ub = UserBenchmark(price.webdriver.FirefoxWebDriver('Selenium'))
	#ub = UserBenchmarkHdd()
	ub.download('test/wip_userbenchmark', 2)
	#data = ub.parse('test/userbenchmark_cpu_fastest_avg_20200123.htm', 'test/userbenchmark_cpu_fastest_avg_20200123_2.htm')
	data = ub.parse_prefixes('test/wip_userbenchmark')
	for d in data:
		if 'brand' in d:
			print('{},\t{},\t{},\t{}'.format(d['brand'], d['model'], d['mfg_code'], d['avg']))
		else:
			print('{},\t{}'.format(d['name'], d['avg']))
