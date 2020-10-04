import bs4
import price.webdatasource
import price.webdriver
import requests

"""PriceSpy's most popular CPUs with 2GHz+ and 4+ cores <= $1000"""
class PriceSpy(price.webdatasource.WebDataSource):

	def download(self, output_file_name_prefix, num_pages=1):
		self.files_downloaded = []
		for i in range(num_pages):
			url_offset = '' if i == 0 else '&offset=' + str(24 * i)
			src = self._download('https://pricespy.co.nz/category.php?k=s334663499&catId=500' + url_offset, 'Find the best deals on CPUs - Compare prices on PriceSpy NZ', 'div[data-test="ProductCard"]', 'body')
			file_name = output_file_name_prefix + '_' + str(i + 1) + '.htm'
			with open(file_name, 'w', encoding='utf-8') as f:
				f.write(src)
			self.files_downloaded.append(file_name)
		return self.files_downloaded
		# page 2: https://pricespy.co.nz/category.php?k=s334663499&catId=500&offset=24

	"""
	Parses PriceSpy data file(s) adding  dictionary objects {'name': <name>, 'price': <e.g. $1,000>'} to result list
	"""
	def parse_soup(self, result, soup):
		product_eles = soup.find_all('div', attrs={'data-test': 'ProductCard'}, limit=24)
		for product_ele in product_eles:
			result.append(self._parse(product_ele))

	def _parse(self, product_ele):
		name_ele = product_ele.find('a', attrs={'aria-label':True})
		name = name_ele['aria-label']
		price_ele = product_ele.find('span', attrs={'data-test': 'PriceLabel'})
		price = price_ele.string
		return {'name': str(name), 'price': str(price)}

"""PriceSpy's most popular internal HDD with 0.9 to 5 TB capacity, 7200/10000 rpm, and less than $500"""
class PriceSpyHdd(price.webdatasource.WebDataSource):

	def download(self, output_file_name_prefix, num_pages=1):
		self.files_downloaded = []
		for i in range(num_pages):
			url_offset = '' if i == 0 else '&offset=' + str(24 * i)
			src = self._download('https://pricespy.co.nz/category.php?k=s332338236&catId=358' + url_offset, 'Find the best deals on Internal Hard Drives - Compare prices on PriceSpy NZ', 'div[data-test="ProductCard"]', 'body')
			file_name = output_file_name_prefix + '_' + str(i + 1) + '.htm'
			with open(file_name, 'w', encoding='utf-8') as f:
				f.write(src)
			self.files_downloaded.append(file_name)
		return self.files_downloaded

	"""
	Parses PriceSpy data file(s) adding  dictionary objects {'name': <name>, 'price': <e.g. $1,000>'} to result list
	"""
	def parse_soup(self, result, soup):
		product_eles = soup.find_all('div', attrs={'data-test': 'ProductCard'}, limit=24)
		for product_ele in product_eles:
			result.append(self._parse(product_ele))

	def _parse(self, product_ele):
		name_ele = product_ele.find('a', attrs={'aria-label':True})
		name = name_ele['aria-label']
		price_ele = product_ele.find('span', attrs={'data-test': 'PriceLabel'})
		price = price_ele.string
		return {'name': str(name), 'price': str(price)}

if __name__ == '__main__':
	#ps = PriceSpy(price.webdriver.FirefoxWebDriver('Selenium'))
	ps = PriceSpyHdd(price.webdriver.FirefoxWebDriver('Selenium'))
	ps.download('test/wip_pricespy', 3)
	data = ps.parse_prefixes('test/wip_pricespy')
	#data = ps.parse('test/pricespy_cpu_pop_4c4t2g_20200123.htm', 'test/pricespy_cpu_pop_4c4t2g_20200123_2.htm')
	for d in data:
		print('{}, {}'.format(d['name'], d['price']))
