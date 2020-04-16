import price.munger

def test_cpu_munge():
	price_data = [
		{'name': 'AMD Athlon 3000G 3.5GHz Socket AM4 Box', 'price': '$1'},
		{'name': 'AMD Ryzen 5 3600 3.6GHz Socket AM4 Box', 'price': '$2'},
		{'name': 'AMD Ryzen 5 3600X 3.8GHz Socket AM4 Box', 'price': '$3'},
		{'name': 'Intel Core i3 9100F 3.6GHz Socket 1151-2 Box', 'price': '$4'}
	]
	perf_data = [
		{'name': 'AMD Ryzen 5 3600', '1-core': 1, '2-core': 2, '8-core': 3, 'avg': 2.5, 'user-rating': None},
		{'name': 'AMD Ryzen 5 3600X', '1-core': 1.5, '8-core': 3.5, 'avg': 3, 'user-rating': 4.5},
		{'name': 'AMD Ryzen TR 2920X', '1-core': 1, '2-core': 2, '8-core': 3, 'avg': 2.5, 'user-rating': 4}
	]
	m = price.munger.CpuMunger()
	munge_result = m.munge(price_data, perf_data)
	munged_data = munge_result['data']
	assert munged_data[0]['name'] == 'AMD Ryzen 5 3600 3.6GHz Socket AM4 Box'
	assert munged_data[0]['1-core/$'] == 0.5
	assert munged_data[0]['2-core/$'] == 1.0
	assert munged_data[0]['8-core/$'] == 1.5
	assert munged_data[0]['avg/$'] == 1.25
	assert munged_data[0]['user-rating/$'] == None
	assert munged_data[1]['name'] == 'AMD Ryzen 5 3600X 3.8GHz Socket AM4 Box'
	assert len(munged_data) == 2
	orphan_price_data = munge_result['orphan_price_data']
	assert orphan_price_data[0]['name'] == 'AMD Athlon 3000G 3.5GHz Socket AM4 Box'
	assert orphan_price_data[1]['name'] == 'Intel Core i3 9100F 3.6GHz Socket 1151-2 Box'
	assert len(orphan_price_data) == 2
	orphan_perf_data = munge_result['orphan_perf_data']
	assert orphan_perf_data[0]['name'] == 'AMD Ryzen TR 2920X'
	assert len(orphan_perf_data) == 1

def test_cpu_canonicalise_pricespy_name():
	m = price.munger.CpuMunger()
	assert m._canonicalise_pricespy_name('AMD Ryzen 5 3600 3.6GHz Socket AM4 Box') == 'AMD Ryzen 5 3600'
	assert m._canonicalise_pricespy_name('AMD Ryzen 5 3600X 3.8GHz Socket AM4 Box') == 'AMD Ryzen 5 3600X'
	assert m._canonicalise_pricespy_name('Intel Core i5 7500 3.4GHz Socket 1151 Box') == 'Intel Core i5-7500'
	assert m._canonicalise_pricespy_name('Intel Core i9 9900K 3.6GHz Socket 1151-2 Box without Cooler') == 'Intel Core i9-9900K'
	assert m._canonicalise_pricespy_name('Intel Core i9-9900KS Special Edition 4.0GHz Socket 1151-2 Box without Cooler') == 'Intel Core i9-9900KS'
	assert m._canonicalise_pricespy_name('AMD Ryzen Threadripper 3970X 3.7GHz Socket sTRX4 Box without Cooler') == 'AMD Ryzen TR 3970X'

def test_hdd_parse_pricespy_name():
	m = price.munger.HddMunger()
	assert_hdd_pricespy_parse_dict(m, 'WD', 64, 1, 'WD1003FZEX', 'WD Black WD1003FZEX 64MB 1TB')
	assert_hdd_pricespy_parse_dict(m, 'Seagate', None, 1, 'ST1000NX0323', 'Seagate Exos 7E2000 ST1000NX0323 4KN 1TB')
	assert_hdd_pricespy_parse_dict(m, 'Seagate', 128, 1.2, 'ST1200MM0009', 'Seagate Enterprise Performance 10K ST1200MM0009 128MB 1.2TB')
	assert_hdd_pricespy_parse_dict(m, 'Seagate', 256, 4, 'ST4000VE001', 'Seagate SkyHawk AI Surveillance ST4000VE001 256MB 4TB')
	assert_hdd_pricespy_parse_dict(m, 'WD', 64, 1, 'WD1000DHTZ', 'WD VelociRaptor WD1000DHTZ 64MB 1TB')

def assert_hdd_pricespy_parse_dict(m, expected_brand, expected_cache, expected_capacity, expected_mfg_code, name):
	parts = m._parse_pricespy_name(name)
	assert name == parts['name']
	assert expected_brand == parts['brand']
	assert expected_cache == parts['cache']
	assert expected_capacity == parts['capacity']
	assert expected_mfg_code == parts['mfg_code']

def test_hdd_munge():
	m = price.munger.HddMunger()
	price_data = [
		{'name': 'WD AV-GP WD20EURX 64MB 2TB', 'price': '$144.61'},
		{'name': 'WD Blue WD10EZEX 64MB 1TB', 'price': '$74.00'},
		{'name': 'Seagate Firecuda ST2000DX002 64MB 2TB', 'price': '$174.75'},
		{'name': 'Seagate Barracuda ST1000DM003 64MB 1TB', 'price': '$85.10'},
		{'name': 'HGST Ultrastar 7K6000 HUS726T4TALE6L4 256MB 4TB', 'price': '$326.63'},
		{'name': 'Seagate ST31000528AS 64MB 1TB', 'price': '$1337'}, # special case
	]
	perf_data = [
		{'brand':'WD', 'mfg_code': '', 'model': 'WD20EURX 2TB', 'samples': 4325, 'avg': 68.3},
		{'brand':'WD', 'mfg_code': 'WD10EZEX', 'model': 'Blue 1TB (2012)', 'samples': 1471343, 'avg': 82.3},
		{'brand': 'Seagate', 'mfg_code': 'ST1000DM003', 'model': 'Barracuda 7200.14 1TB', 'samples': 912952, 'avg': 88.2},
		{'brand': 'Seagate', 'mfg_code': 'ST2000DX002', 'model': 'FireCuda SSHD 2TB (2016)', 'samples': 59147, 'avg': 83.6},
		{'brand': 'Seagate', 'mfg_code': '', 'model': 'ST310005 28AS 1TB', 'samples': 6552, 'avg': 50.4}, # mfg_code empty and model has a space
	]
	munge_result = m.munge(price_data, perf_data)
	munged_data = munge_result['data']
	assert munged_data[0]['name'] == 'Seagate Barracuda ST1000DM003 64MB 1TB'
	assert munged_data[0]['avg'] ==  88.2
	assert munged_data[0]['avg/$'] ==  1.036
	assert munged_data[0]['capacity'] ==  1
	assert munged_data[0]['capacity/$'] ==  0.012
	assert munged_data[0]['$/capacity'] ==  85.10
	assert munged_data[0]['price'] ==  '$85.10'
	assert munged_data[1]['name'] == 'Seagate Firecuda ST2000DX002 64MB 2TB'
	assert munged_data[1]['avg'] ==  83.6
	assert munged_data[1]['capacity'] ==  2
	assert munged_data[1]['capacity/$'] ==  0.011
	assert munged_data[1]['$/capacity'] ==  87.38
	assert munged_data[1]['price'] ==  '$174.75'
	assert munged_data[2]['name'] == 'Seagate ST31000528AS 64MB 1TB'
	assert munged_data[2]['avg'] ==  50.4
	assert munged_data[2]['capacity'] == 1
	assert munged_data[2]['capacity/$'] ==  0.001
	assert munged_data[2]['$/capacity'] ==  1337
	assert munged_data[2]['price'] ==  '$1337'
	assert munged_data[3]['name'] == 'WD AV-GP WD20EURX 64MB 2TB'
	assert munged_data[3]['avg'] ==  68.3
	assert munged_data[3]['capacity'] ==  2
	assert munged_data[3]['capacity/$'] ==  0.014
	assert munged_data[3]['$/capacity'] ==  72.31
	assert munged_data[3]['price'] ==  '$144.61'
	assert munged_data[4]['name'] == 'WD Blue WD10EZEX 64MB 1TB'
	assert munged_data[4]['avg'] ==  82.3
	assert munged_data[4]['capacity'] ==  1
	assert munged_data[4]['capacity/$'] ==  0.014
	assert munged_data[4]['$/capacity'] ==  74.00
	assert munged_data[4]['price'] ==  '$74.00'

	assert 0 == len(munge_result['orphan_perf_data'])
	assert 1 == len(munge_result['orphan_price_data'])
	assert munge_result['orphan_price_data'][0]['name'] == 'HGST Ultrastar 7K6000 HUS726T4TALE6L4 256MB 4TB'
