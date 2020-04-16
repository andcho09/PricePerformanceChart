import copy
import re

class CpuMunger:

	"""
	Munges together price and performance data together by matching on names (with some reformatting)

	Input is:
	- price_data - list of dictionaries (name, price)
	- perf_data - list of dictionaries (name, performance attribute 1, performance attribute 2...)

	Output is a dictionary of { 'data': [ combined dictionary  ], 'orphan_price_data': [ price_data ], 'orphan_perf_data': [ perf_data] }
	"""
	def munge(self, price_data, perf_data):
		orphan_price_data = copy.deepcopy(price_data)
		orphan_price_data.sort(key = lambda x: x['name'])
		orphan_perf_data = copy.deepcopy(perf_data)
		orphan_perf_data.sort(key = lambda x: x['name'])
		data = []

		for price_data_row in reversed(orphan_price_data): # Reverse order because looping and deleting will skip items
			name = self._canonicalise_pricespy_name(price_data_row['name'])
			index = self._find_name(orphan_perf_data, name)
			if index >= 0:
				perf_item = orphan_perf_data[index]
				perf_item.update(price_data_row) # Update dict with pricespy name and price
				del orphan_perf_data[index]
				orphan_price_data.remove(price_data_row)
				data.insert(0, perf_item)
		return {
			'data': self.enrich_price_performance(data),
			'orphan_price_data': orphan_price_data,
			'orphan_perf_data': orphan_perf_data
		}

	"""
	Update given dictionary with performance per price for each performance attribute.
	"""
	def enrich_price_performance(self, data):
		for row in data:
			if 'price' not in row:
				return
			price = float(row['price'].replace('$', '').replace(',', ''))
			_calc_price_performance(row, '1-core', price)
			_calc_price_performance(row, '2-core', price)
			_calc_price_performance(row, '8-core', price)
			_calc_price_performance(row, 'avg', price)
			_calc_price_performance(row, 'user-rating', price)
			row['avg'] = round(float(row['avg']), 1)
		return data

	"""
	Extract the model number from the PriceSpy name so we can match CPUs against UserBenchmark's names
	"""
	def _canonicalise_pricespy_name(self, name):
		name = self.p_speed_socket_cooler.sub('', name)
		name = self.p_intel.sub('Intel Core i\\1-', name)
		name = self.p_intel_special_ed.sub('KS', name)
		name = self.p_amd_threadripper.sub('AMD Ryzen TR ', name)
		return name

	# Patterns
	p_speed_socket_cooler = re.compile(' [0-9]\\.?[0-9]?[0-9]?GHz Socket .* Box( without Cooler)?')
	p_intel = re.compile('Intel Core i([0-9]+) ')
	p_intel_special_ed = re.compile('KS Special Edition')
	p_amd_threadripper = re.compile('AMD Ryzen Threadripper ')

	"""
	Finds the index of the dictionary item with the given name in the 'name' attribute. Returns -1 if not found.
	"""
	def _find_name(self, list, name):
		for i, item in enumerate(list):
			if 'name' in item and item['name'] == name:
				return i
		return -1

class HddMunger:

	"""
	Munges together price and performance data together. Note this will produce an empty list for 'orphan_perf_data' because it's huge.

	Input is:
	- price_data - list of dictionaries (name, price)
	- perf_data - list of dictionaries (brand, mfg_code, model, avg)

	Output is a dictionary of { 'data': [ combined dictionary  ], 'orphan_price_data': [ price_data ], 'orphan_perf_data': [<empty list>] }
	"""
	def munge(self, price_data, perf_data):
		orphan_price_data = copy.deepcopy(price_data)
		orphan_price_data.sort(key = lambda x: x['name'])
		perf_index = self._build_perf_index(perf_data)
		data = []

		for price_data_row in reversed(orphan_price_data): # Reverse order because looping and deleting will skip items
			product_parts = self._parse_pricespy_name(price_data_row['name'])
			mfg_code = product_parts['mfg_code']
			if mfg_code is not None and mfg_code.lower() in perf_index['mfg_codes']:
				perf_item = perf_index['mfg_codes'][mfg_code.lower()]
				product_parts['model'] = perf_item['model'] # Copy some attributes from the perf data
				product_parts['avg'] = perf_item['avg']
				product_parts['price'] = price_data_row['price']
				orphan_price_data.remove(price_data_row)
				data.insert(0, product_parts)

		return {
			'data': self.enrich_price_performance(data),
			'orphan_price_data': orphan_price_data,
			'orphan_perf_data': []
		}

	"""Builds a index of the performance data so it's can be searched quickly."""
	def _build_perf_index(self, perf_data):
		index = {'uniq_brands': [], 'mfg_codes':{}}
		missing_mfg_code_data = []
		for perf in perf_data:
			brand = perf['brand']
			if brand is not None and len(brand) != 0 and brand.lower() not in index['uniq_brands']:
				index['uniq_brands'].append(brand.lower())
			mfg_code = perf['mfg_code']
			if mfg_code is not None and len(mfg_code) != 0:
				index['mfg_codes'][mfg_code.lower()] = perf
			else:
				missing_mfg_code_data.append(perf) # Try to infer model later

		for perf in missing_mfg_code_data:
			model = perf['model']
			if model is not None and len(model) > 0:
				model = self.p_capacity.sub('', model, count=1)

				# Special cases...
				parse_model = True
				if model == 'ST310005 28AS':
					model = 'ST31000528AS'
				elif model == 'OCZ-AGILITY3': # These are SSDs
					continue

				mfg_code = self._get_longest_word_from_model(model).lower() if parse_model else model.lower()
				if mfg_code != '' and mfg_code not in index['mfg_codes']: # Don't overwrite a model number we got directly from the csv
					perf['mfg_code'] = mfg_code
					index['mfg_codes'][mfg_code.lower()] = perf

		index['uniq_brands'] = index['uniq_brands'].sort()
		return index

	# Patterns
	p_brand = re.compile('^([A-z0-9]+) ')
	p_cache = re.compile(' ([1-9][0-9][0-9]?)MB ')
	p_capacity = re.compile(' ([0-9.]+)TB$')

	"""
	Attempts to parse the name into a dictionary of format: {name, brand, capacity, cache, mfg_code} where 'name' is the
	original name. If an element can't be found, the dictionary value is None.
	"""
	def _parse_pricespy_name(self, name):
		brand = None
		cache = None
		capacity = None
		mfg_code = None

		match = self.p_brand.search(name)
		if match is not None:
			brand = match.group(1)
		match = self.p_cache.search(name)
		if match is not None:
			cache = match.group(1) # could be empty
		match = self.p_capacity.search(name)
		if match is not None:
			capacity = match.group(1) # could be empty

		# Get rid of the known parts of the name
		stripped_name = name.replace(brand + ' ', ' ').replace(' ' + str(capacity) + 'TB', ' ')
		if cache is not None:
			stripped_name = stripped_name.replace(' ' + cache + 'MB' + ' ', '')

		# Guess the mfg_code by taking the longest remaining string
		mfg_code = self._get_longest_word_from_model(stripped_name)

		return { 'name': name, 'brand': brand, 'cache': None if cache is None else int(cache), 'capacity': None if capacity is None else float(capacity), 'mfg_code': mfg_code }

	"""Returns the longest word from the model name (split by space). If not found, returns the empty string."""
	def _get_longest_word_from_model(self, model):
		mfg_code = ''
		name_components = model.strip().split(' ')
		for name_component in name_components:
			if name_component in ['Surveillance', 'Technology', 'VelociRaptor']: # blacklist words we know aren't mfg_code
				continue
			if len(name_component) > len(mfg_code):
				mfg_code = name_component
		return mfg_code

	"""
	Update given dictionary with performance per price for each performance attribute.
	"""
	def enrich_price_performance(self, data):
		for row in data:
			if 'price' not in row:
				return
			price = float(row['price'].replace('$', '').replace(',', ''))
			_calc_price_performance(row, 'avg', price)
			_calc_price_performance(row, 'capacity', price)
			_calc_price_performance(row, 'capacity', price, True)
			row['avg'] = round(float(row['avg']), 1)
		return data

"""
Formats the munged data for printing or logging
"""
def format(data):
	result = 'Combined Data:\n'
	for row in data['data']:
		result += ' {} ({}): avg={}\n'.format(row['name'], row['price'], row['avg'])
	result += 'Orphan Price Data:\n'
	for row in data['orphan_price_data']:
		result += ' ' + row['name'] + '\n'
	result += 'Orphan Performance Data:\n'
	for row in data['orphan_perf_data']:
		result += ' ' + row['name'] + '\n'
	return result

"""
Adds an attribute whose name is '<attribute>/$' and value is divided by the price. Parameters:
- row - the dictionary to manipulate
- perf_attribute - the name of the attribute in the data to divide by price
- price - the price
- invert - default is False, divide attribute by price as '<attribute>/$'. Use True to divide price by attribute as '$/<attribute>'
"""
def _calc_price_performance(row, perf_attribute, price, invert=False):
		if perf_attribute in row and row[perf_attribute] != None:
			if invert:
				row['$/' + perf_attribute] = round(price / float(row[perf_attribute]), 2)
			else:
				row[perf_attribute + '/$'] = round(float(row[perf_attribute]) / price, 3)
		else:
			row[perf_attribute + '/$'] = None