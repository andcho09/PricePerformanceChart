import abc
import bs4
import price.helper
import os
import selenium.webdriver.support.wait

logger = price.helper.get_logger(__name__)

"""
Abstracts Selenium scraping the HTML DOM from a web site. Requirements:
"""
class WebDataSource(metaclass=abc.ABCMeta):

	"""
	Parameters:
	- webdriver - a webdriver.WebDriver which abstracts away the Selenium web driver
	"""
	def __init__(self, webdriver):
		self.webdriver = webdriver

	"""
	Download HTML DOM from this web data source. Uses Selenium to hit web pages with Firefox.

	Parameters:
	- output_file_name_prefix - output is saved to a file with this prefix. Suffix is '_<page_number>.htm'
	- num_pages - number of pages of results to download. Default is 1

	Returns a list of the files downloaded
	"""
	@abc.abstractmethod
	def download(self, output_file_name_prefix, num_pages=1):
		raise NotImplementedError

	"""
	Downloads HTML source for the given tag. Parameters:
	- url - web site to download
	- page_title - expected page title (using 'in' check) to verify we're hitting the right page. Returns assertion error if this check fails
	- wait_until_css_selector - Wait a maximum 10 seconds for the element defined by the CSS selector to be present before returning HTML source
	- tag - name of tag to return HTML source for
	Returns: the HTML as a string
	"""
	def _download(self, url, page_title, wait_until_css_selector, tag):
		result = None
		self.driver = self.webdriver.getWebDriver()
		try:
			self.driver.get(url)
			assert page_title in self.driver.title
			self._pre_wait_navigation(self.driver)
			selenium.webdriver.support.wait.WebDriverWait(self.driver, 10).until(lambda x: x.find_element_by_css_selector(wait_until_css_selector))
			elem = self.driver.find_element_by_tag_name(tag)
			result = elem.get_attribute('outerHTML')
			self._post_download(self.driver)
		finally:
			try:
				self.driver.close()
			except Exception as e:
				logger.warn('Closing selenium browser had an error:' + str(e))
		return result

	"""Allow subclasses to do Selenium navigation before waiting for the CSS selector and downloading source"""
	def _pre_wait_navigation(self, driver):
		pass

	"""Allow subclasses to do Selenium actions after source has been downloaded. Useful for single-page sites to download page 2."""
	def _post_download(self, driver):
		pass

	"""Quit the Selenium session. Frees up some processes/resources."""
	def quit_selenium(self):
		if hasattr(self, 'driver'):
			try:
				self.driver.quit()
			except Exception as e:
				logger.warn('Quitting selenium session had an error:' + str(e))

	"""Parse this web data source returning a list of dictionary objects"""
	def parse(self, *input_file_paths):
		result = []
		for input_file_path in input_file_paths:
			with open(input_file_path, 'r') as f:
				soup = bs4.BeautifulSoup(f.read(), 'html.parser')
				self.parse_soup(result, soup)
		return result

	"""
	Parse files with the given prefix and suffix (default is '.htm') in the format '<prefix>_<1-based index><suffix>'
	returning a list of dictionary objects. Index must be sequential and start at 1.
	"""
	def parse_prefixes(self, prefix, suffix='.htm'):
		result = []
		i = 1
		input_file_path = prefix + '_' + str(i) + suffix
		while os.path.exists(input_file_path):
			with open(input_file_path, 'r') as f:
				soup = bs4.BeautifulSoup(f.read(), 'html.parser')
				self.parse_soup(result, soup)
			i = i + 1
			input_file_path = prefix + '_' + str(i) + suffix
		return result

	"""Parse a Beautiful Soup object representing this web data source's HTML DOM adding results to the result array"""
	@abc.abstractmethod
	def parse_soup(self, result, soup):
		raise NotImplementedError
