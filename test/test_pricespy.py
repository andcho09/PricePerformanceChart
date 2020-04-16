import bs4
import os
import price.pricespy
import pytest

def test_parse():
	ps = price.pricespy.PriceSpy(None)
	data = ps.parse('test/pricespy_cpu_20200314_1.htm')
	data.sort(key = lambda x: x['name'])

	assert len(data) == 24
	assertPrice('AMD Ryzen 3 3200G 3.6GHz Socket AM4 Box', '$164.85', data[0])
	assertPrice('AMD Ryzen 5 2600 3.4GHz Socket AM4 Box', '$226.50', data[1])
	assertPrice('AMD Ryzen 5 3400G 3.7GHz Socket AM4 Box', '$265.00', data[2])
	assertPrice('Intel Core i9 9900K 3.6GHz Socket 1151-2 Box without Cooler', '$869.00', data[21])
	assertPrice('Intel Core i9 9900KF 3.6GHz Socket 1151-2 Box without Cooler', '$810.00', data[22])
	assertPrice('Intel Core i9-9900KS Special Edition 4.0GHz Socket 1151-2 Box without Cooler', '$1,099.00', data[23])

def assertPrice(expected_name, expected_price, actual):
	assert expected_name == actual['name']
	assert expected_price == actual['price']

# Globals for test_download
PREFIX = 'test/test_webdatasource_test_pricespy'
PRICESPY_FILE = PREFIX + '_1.htm'
PS = None

def setup_function(func):
	if os.path.isfile(PRICESPY_FILE):
		os.remove(PRICESPY_FILE)
	global PS
	PS = price.pricespy.PriceSpy(price.webdriver.FirefoxWebDriver('Selenium'))

def teardown_function(func):
	if PS is not None:
		PS.quit_selenium()

@pytest.mark.slow # this is slow
def test_download():
	PS.download(PREFIX, num_pages=1)
	assert os.path.isfile(PRICESPY_FILE)
	with open(PRICESPY_FILE, 'r', encoding='utf-8') as f:
		soup = bs4.BeautifulSoup(f.read(), 'html.parser')
		assert 24 == len(soup.find_all('div', attrs={'data-test': 'ProductCard'}))
