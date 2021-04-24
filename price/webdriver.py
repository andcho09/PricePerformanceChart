import abc
import selenium.webdriver
import selenium.webdriver.firefox.options
import selenium.webdriver.chrome.options

"""
Abstracts the Selenium WebDriver away from the rest of the code base. Allows subclasses to implement the Firefox and Chrome specifics.

Requirements for Chrome:
- Chrome installed on path or at least specified with the 'chrome_binary' argument
- ChromeDriver (https://chromedriver.chromium.org/downloads) installed on path or specified with the 'chromedriver_path' argument

Requirements for Firefox:
- Firefox installed on path or at least specified with the 'firefox_binary' argument
- GeckoDriver (https://github.com/mozilla/geckodriver/releases) installed on path or specified with the 'geckodriver_path' argument
- Additionally a Firefox profile can be specified with the 'profile' argument which is useful if the default profile has extensions that
	would interfere with the scrape


Note, it is highly likely the combination of browser version and driver version are extremely interlinked therefore prone to breaking when
either changes (e.g. Chrome auto-updates itself).
"""
class WebDriver(metaclass=abc.ABCMeta):

	"""
	Returns a selenium.webdriver.remote.webdriver.WebDriver
	"""
	@abc.abstractmethod
	def getWebDriver(self):
		raise NotImplementedError


"""
WebDriver based on Firefox. Note The ChromeWebDriver appears to be more stable.
"""
class FirefoxWebDriver(WebDriver):

	"""
	Parameters:
	- profile - Firefox profile for Selenium to use, if None the default is used
	- firefox_binary - path to Firefox, if None the default installation is used
	- geckodriver_path - directory with the GeckoDriver, if None will look on the path for it
	- geckodriver_log_file - path for GeckoDriver to write logs to. If None will use the default
	"""
	def __init__(self, profile=None, firefox_binary=None, geckodriver_path='geckodriver', geckodriver_log_file='geckodriver.log'):
		self.profile = profile
		self.firefox_binary = firefox_binary
		if geckodriver_path is None:
			self.geckodriver_path = 'geckodriver'
		else:
			self.geckodriver_path = geckodriver_path
		if geckodriver_log_file is None:
			self.geckodriver_log_file = 'geckodriver.log'
		else:
			self.geckodriver_log_file = geckodriver_log_file

	def getWebDriver(self):
		ff_options = selenium.webdriver.firefox.options.Options()
		ff_options.headless = True
		if self.profile is not None: # Not using the firefox_profile arg here since it requires specifying the path to the profile's directory
			ff_options.add_argument('-p')
			ff_options.add_argument(self.profile)
		return selenium.webdriver.Firefox(firefox_binary=self.firefox_binary, executable_path=self.geckodriver_path, options=ff_options, service_log_path=self.geckodriver_log_file)

"""
WebDriver based on Chrome/Chromium.
"""
class ChromeWebDriver(WebDriver):

	"""
	Parameters:
	- chrome_binary - path to Chrome, if None the default installation is used
	- geckodriver_path - directory with the GeckoDriver, if None will look on the path for it
	- geckodriver_log_file - path for GeckoDriver to write logs to. If None will use the default
	- temp_dir - directory which Chrome can use to write to. Defaults to /tmp
	"""
	def __init__(self, chrome_binary=None, chromedriver_path='chromedriver', chromedriver_log_file='chromedriver.log', temp_dir='/tmp'):
		self.chrome_binary = chrome_binary
		if chromedriver_path is None:
			self.chromedriver_path = 'chromedriver'
		else:
			self.chromedriver_path = chromedriver_path
		if chromedriver_log_file is None:
			self.chromedriver_log_file = 'chromedriver.log'
		else:
			self.chromedriver_log_file = chromedriver_log_file
		self.temp_dir = temp_dir

	def getWebDriver(self):
		options = selenium.webdriver.ChromeOptions()
		options.binary_location = self.chrome_binary
		# Options from https://aws.amazon.com/blogs/devops/ui-testing-at-scale-with-aws-lambda/
		options.add_argument('--data-path=' + self.temp_dir + '/data-path') # This directory doesn't seem to get created
		options.add_argument('--disable-gpu') # Not in https://github.com/alixaxel/chrome-aws-lambda but in https://github.com/adieuadieu/serverless-chrome/blob/master/packages/lambda/builds/chromium/Dockerfile
		options.add_argument('--disk-cache-dir=' + self.temp_dir + '/cache-dir')
		options.add_argument('--headless')
		options.add_argument('--homedir=' + self.temp_dir)
		options.add_argument('--no-sandbox')
		options.add_argument('--single-process')
		options.add_argument('--user-data-dir=' + self.temp_dir + '/user-data')
		options.add_argument('--window-size=1366,768')
		# Options from https://github.com/alixaxel/chrome-aws-lambda
		options.add_argument('--disable-background-timer-throttling')
		options.add_argument('--disable-breakpad')
		options.add_argument('--disable-client-side-phishing-detection')
		options.add_argument('--disable-cloud-import')
		options.add_argument('--disable-default-apps')
		options.add_argument('--disable-dev-shm-usage')
		options.add_argument('--disable-extensions')
		options.add_argument('--disable-gesture-typing')
		options.add_argument('--disable-hang-monitor')
		options.add_argument('--disable-infobars')
		options.add_argument('--disable-notifications')
		options.add_argument('--disable-offer-store-unmasked-wallet-cards')
		options.add_argument('--disable-offer-upload-credit-cards')
		options.add_argument('--disable-popup-blocking')
		options.add_argument('--disable-print-preview')
		options.add_argument('--disable-prompt-on-repost')
		options.add_argument('--disable-setuid-sandbox')
		options.add_argument('--disable-speech-api')
		options.add_argument('--disable-sync')
		options.add_argument('--disable-tab-for-desktop-share')
		options.add_argument('--disable-translate')
		options.add_argument('--disable-voice-input')
		options.add_argument('--disable-wake-on-wifi')
		options.add_argument('--disk-cache-size=33554432')
		options.add_argument('--enable-async-dns')
		options.add_argument('--enable-simple-cache-backend')
		options.add_argument('--enable-tcp-fast-open')
		options.add_argument('--enable-webgl')
		options.add_argument('--hide-scrollbars')
		options.add_argument('--ignore-gpu-blacklist')
		options.add_argument('--media-cache-size=33554432')
		options.add_argument('--metrics-recording-only')
		options.add_argument('--mute-audio')
		options.add_argument('--no-default-browser-check')
		options.add_argument('--no-first-run')
		options.add_argument('--no-pings')
		#options.add_argument('--no-sandbox') # above
		options.add_argument('--no-zygote')
		options.add_argument('--password-store=basic')
		options.add_argument('--prerender-from-omnibox=disabled')
		options.add_argument('--use-gl=swiftshader')
		options.add_argument('--use-mock-keychain')
		options.add_argument('--memory-pressure-off')

		return selenium.webdriver.Chrome(self.chromedriver_path, options=options, service_log_path=self.chromedriver_log_file)
