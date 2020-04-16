import boto3
import bs4
import os
import price.helper
import price.userbenchmark
import pytest

def test_cpu_parse():
	ub = price.userbenchmark.UserBenchmark(None)
	data = ub.parse('test/userbenchmark_cpu_20200314_1.htm')
	data.sort(key = lambda x: x['name'])

	assert len(data) == 50
	assertPrice('AMD Ryzen 5 3500', '88', data[0])
	assertPrice('AMD Ryzen 5 3500X', '88.9', data[1])
	assertPrice('AMD Ryzen 5 3600', '88.3', data[2])
	assertPrice('Intel Core i9-9960X', '88.7', data[47])
	assertPrice('Intel Core i9-9980HK', '84.7', data[48])
	assertPrice('Intel Core i9-9980XE', '86', data[49])

# Test parsing the page in US currency which shows extra links
def test_cpu_parse_us():
	ub = price.userbenchmark.UserBenchmark(None)
	data = ub.parse('test/userbenchmark_us_20200309_1.htm')
	data.sort(key = lambda x: x['name'])
	assertPrice('AMD Ryzen 3 2200G', '66.8', data[0])
	assertPrice('AMD Ryzen 5 1500X', '66.6', data[1])
	assertPrice('Intel Pentium G4560', '53.7', data[49])

def assertPrice(expected_name, expected_perf, actual):
	assert expected_name == actual['name']
	assert expected_perf == actual['avg']

# Globals for test_download
PREFIX = 'test/test_webdatasource_test_userbenchmark'
USERBENCHMARK_FILE = PREFIX + '_1.htm'
UB = None

def setup_function(func):
	if os.path.isfile(USERBENCHMARK_FILE):
		os.remove(USERBENCHMARK_FILE)
	global UB
	price.helper.init_environ()
	UB = price.userbenchmark.UserBenchmark(price.webdriver.ChromeWebDriver(temp_dir=os.path.abspath('build')))

def teardown_function(func):
	if UB is not None:
		UB.quit_selenium()

@pytest.mark.slow # this is slow
def test_cpu_download():
	UB.download(PREFIX, num_pages=1)
	assert os.path.isfile(USERBENCHMARK_FILE)
	data = UB.parse(USERBENCHMARK_FILE)
	# Assert there are 50 results and that they're in descending order of average effective speed (i.e. sorting is correct; let's just check the first 10)
	assert len(data) == 50
	current_avg = 99999
	for i in range(0, 10):
		product = data[i]
		product_avg = float(product['avg'])
		assert product_avg <= current_avg, 'The product ' + str(product) + ' at index ' + str(i) + ' is not slower or equal to ' + str(current_avg)
		current_avg = product_avg

def test_hdd():
	ub_hdd = price.userbenchmark.UserBenchmarkHdd()
	ub_hdd.download(USERBENCHMARK_FILE)
	assert os.path.isfile(USERBENCHMARK_FILE)

	data = ub_hdd.parse(USERBENCHMARK_FILE)
	assert len(data) >= 450
	product = data[0]
	assert is_blank(product['avg']) == False
	assert is_blank(product['brand']) == False
	assert is_blank(product['model']) == False
	assert is_blank(product['mfg_code']) == False

def is_blank(text):
	if text == None or len(text.strip()) == 0:
		return True
	return False

