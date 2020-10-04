import argparse
import boto3
import datetime
import json
import os
import price.helper
import price.munger
import price.pricespy
import price.scraper
import price.userbenchmark
import price.webdriver
import sys
import time

logger = price.helper.get_logger(__name__, stream=sys.stdout)

def _add_browser_opts(parser):
	parser.add_argument('-c', '--chrome', action='store_true', help='download with Chrome (default)')
	parser.add_argument('-f', '--firefox', action='store_true', help='download with Firefox')

if __name__ == '__main__': # this hack prevents this code from being run during 'py -m pytest' runs
	# Allow all arguments to be passed as arguments on the CLI
	epilog = """possible actions are:
  d   download HTML, parse HTML, munge data, and write locally to 'web' directory
  m   parse HTML, munge data, and write locally to 'web' directory
  u   upload latest JSON data file from local 'web' directory into S3"""
	parser = argparse.ArgumentParser(description='Welcome to the Price Performance Chart!', formatter_class=argparse.RawTextHelpFormatter, epilog=epilog)
	parser.add_argument('-v', '--version', action='store_true', help="show browser versions")
	_add_browser_opts(parser) # Add options here so it shows on the main (no product 'type' subcommand) help
	subparsers = parser.add_subparsers(title='product types to operate on', dest='type')
	for product_type in ['cpu', 'hdd']:
		msg = 'Operate on ' + product_type.upper() + ' information'
		subparser = subparsers.add_parser(product_type, description=msg, help=msg, formatter_class=argparse.RawTextHelpFormatter, epilog=epilog)
		subparser.add_argument('action', choices=['d', 'm', 'u'], help='Action to take', nargs ='?')
	args = parser.parse_args()
	if not hasattr(args, 'action'):
		setattr(args, 'action', None) # Hack args.action = None to make prompt behaviour below easier

	if args.version:
		results = []
		driver = price.webdriver.ChromeWebDriver(temp_dir=os.path.abspath('build')).getWebDriver()
		results.append(('Chrome', driver.capabilities["browserVersion"]))
		driver = price.webdriver.FirefoxWebDriver('Selenium').getWebDriver()
		results.append(('Firefox', driver.capabilities["browserVersion"]))
		for result in results:
			print(f'{result[0]} browser version: {result[1]}')
		sys.exit(0)

	# Preserve old behaviour of prompting which makes debugging nice
	if args.type is None:
		parser.print_help()
		print()
	while args.type is None:
		response = input("What product type do you want operate on {cpu,hdd}? ")
		if response.lower() == 'cpu':
			args.type = 'cpu'
		elif response.lower() == 'hdd':
			args.type = 'hdd'
	while args.action is None:
		response = input("What action to take {d,m,u}? ")
		if response.lower() == 'd':
			args.action = 'd'
		elif response.lower() == 'm':
			args.action = 'm'
		elif response.lower() == 'u':
			args.action = 'u'
	if args.chrome == False and args.firefox == False:
		args.chrome = True # Chrome is default

	webdriver = price.webdriver.ChromeWebDriver(temp_dir=os.path.abspath('build')) if args.chrome else price.webdriver.FirefoxWebDriver('Selenium')
	today = datetime.date.today().strftime("%Y%m%d")
	pricespy_prefix = 'test/pricespy_' + args.type + '_' + today
	userbenchmark_prefix = 'test/userbenchmark_' + args.type + '_' + today + ('.csv' if args.type == 'hdd' else '')
	data_file = 'web/price_performance_' + args.type + '_' + today + '.json'
	price.helper.init_environ()
	scraper = price.scraper.Scraper(pricespy_prefix, userbenchmark_prefix, webdriver, price.scraper.Type.CPU if args.type == 'cpu' else price.scraper.Type.HDD)

	if args.action == 'd':
		scraper.download()
		scraper.quit_selenium()
		print('Downloaded: ' + str(scraper.all_files_downloaded))

	if args.action == 'd' or args.action == 'm':
		data = scraper.parse()
		data = scraper.munge(data['pricespy_data'], data['userbenchmark_data'])
		with open(data_file, 'w', encoding='utf-8') as f:
			f.write(json.dumps(data['data']))
		print(price.munger.format(data))

		with open('web/latest_' + args.type + '.js', 'w', encoding='utf-8') as f:
			f.write('var LATEST_' + args.type.upper() +'_DATA_FILE="price_performance_' + args.type + '_' + today + '.json' + '";')
		print('Munge complete. #Combined={0}, #OrphanPrice={1}, #OrphanPerformance={2}'.format(len(data['data']), len(data['orphan_price_data']), len(data['orphan_perf_data'])))

	if args.action == 'u':
		candidate_files = os.listdir('web')
		candidate_files.reverse()
		json_data = None
		for candidate_file in candidate_files:
			if candidate_file.startswith('price_performance_'):
				with open('web/' + candidate_file, 'r') as f:
					json_data = f.read()
				print('Uploading to data file S3: web/' + candidate_file)
				break
		s3_details = price.helper.get_s3_details()
		scraper.upload_data_to_s3(s3_details.client, s3_details.bucket, s3_details.key_prefix, json_data)
