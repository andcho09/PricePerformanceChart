# Price Performance Chart

Chart CPUs sorted by price-performance where:

* price is from [PriceSpy](https://pricespy.co.nz/category.php?k=s331848943&catId=500) (most popular 2-5 GHz, 4+ cores)
* performance is from [UserBenchmark](https://cpu.userbenchmark.com/) (fastest average effective speed)

UserBenchmark is great but the "best value for money" sorting uses US retailers so is missing out on local NZ retailers. 

This also serves as a proof-of-concept for running Selenium within AWS Lambda. Note that UserBenchmark does have a [CSV download](https://www.userbenchmark.com/page/developer) (just effective speed metric though) so scraping with Selenium isn't the only method to  retrieve data.

## Usage Guide

### Viewing Charts

1. Launch web server
1. Navigate to ``/chart.htm``

### Regenerating Charts

1. Activate ``venv``

	```
	$ .venv/Scripts/activate
	```

1. Run ``main.py`` and select option to download the data from PriceSpy/UserBenchmark, munge downloaded PriceSpy/UserBenchmark data together, or upload munged data to AWS S3

	```
	$ py main.py
	```

1. Or to run individual modules for testing

	```
	$ py -m price.pricespy
	```

## Development Guide

### Setup

This section assumes ``venv`` is being used

1. Create venv environment

	```
	$ python -m venv .venv
	```

1. Activate venv environment

	```
	$ .venv\Scripts\activate
	```

1. Install pip modules

	```
	$ pip install -r requirements.txt
	```

1. For local development

	1. the ChromeDriver (to be used with Chrome/Chromium) and/or the GeckoDriver (to be used with Firefox) should be placed on the path. See [lambda_layer/NOTES.md](lambda_layer/NOTES.md) for download links.
	1. regular Chrome/Firefox can be installed (be careful of version dependencies with the browser version).

### Testing

```
$ py -m pytest
```

Note, this runs all of the tests, including the ones that invoke Selenium with a browser so will ~30 seconds to run. If you only want to certain tests run

* browser tests only (slow):

		$ py -m pytest -m "slow"

* non-browser (fast):

		$ py -m pytest -m "not slow"


**TODO**: these tests currently do not invoke doesn't Selenium/browser

### Updating Python dependencies

1. In a VirtualEnv environment...
1. Update whatever dependencies (i.e. ``pip install -U <dependency>``) and retest
1. Freeze dependencies

	```
	$ pip freeze > requirements.txt
	```

1. Check Ant ``build.xml`` doesn't need to be updated (it filters in/out dependencies to keep the package small)


## Deploying To AWS

There are three major steps:

1. Prepare the Lambda layer (i.e. the headless Chromium and ChromeDriver dependencies)
1. Update the Lambda code (i.e. the actual Lambda code that does the scraping)
1. Upload static web content

### 1) Prepare Lambda layer

This step can be skipped if the layer has not been modified and has already been published to Lambda. Otherwise, see [lambda_layer/NOTES.md](lambda_layer/NOTES.md) for details.

### 2) Update the Lambda code

Note, the ``ant deploy`` target will do the first 3 steps for you (i.e. will create the change set).

1. Package CloudFormation template (i.e. upload code to S3) and copy template to S3 (note this is a Unix command)

	```
	$ aws cloudformation package --template-file template.yaml --output-template-file build/packaged-ppc-scraper-template.yaml --s3-prefix priceperformancechart/scraper-releases/$(date +%Y-%m-%d) --s3-bucket my-cloudformation-bucket-ap-southeast-2 --region ap-southeast-2
	```

1. Upload template to S3

	```
	$ aws s3 cp build/packaged-ppc-scraper-template.yaml s3://my-cloudformation-bucket-ap-southeast-2/priceperformancechart/templates/
	```

1. Update (or create) the CloudFormation stack (note this is a Unix command)

	```
	$ aws cloudformation create-change-set --stack-name PricePerformanceChartStack --change-set-name Change-$(date +%Y-%m-%d-%H%M) --tags Key=Project,Value=PricePerformanceChart --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND --template-url https://my-cloudformation-bucket-ap-southeast-2.s3-ap-southeast-2.amazonaws.com/priceperformancechart/templates/packaged-ppc-scraper-template.yaml --parameters ParameterKey=DebugEnabled,ParameterValue=true --region ap-southeast-2
	```

	Note if the stack doesn't exist yet, add the ``--change-set-type CREATE`` flag

	```
	$ aws cloudformation create-stack --stack-name PricePerformanceChartStack --tags Key=Project,Value=PricePerformanceChart --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND --template-url https://my-cloudformation-bucket-ap-southeast-2.s3-ap-southeast-2.amazonaws.com/priceperformancechart/templates/packaged-ppc-scraper-template.yaml --parameters ParameterKey=DebugEnabled,ParameterValue=true --region ap-southeast-2
	```

1. Execute the change set from CloudFormation or CLI

### 3) Upload static web content

Run ``ant web``

## Troubleshooting

### WebDriverException... Status code was: 127

**Looks like:**

> [ERROR] WebDriverException: Message: Service /opt/chromedriver80/chromedriver unexpectedly exited. Status code was: 127

**Caused by:** Likely missing ``.so*`` library files or mismatched Chrome-ChromeDriver versions

**Resolve by:** Invoke the "TestDriver" test event in Lambda (i.e. send ``{"driver": "value1"}``) which will attempt to start the ChromeDriver itself without Chromium. If successful, it will await commands and Lambda will kill it after the function times out. If it fails, a useful error message in the log will be printed.

If it says a .so library file is missing, see [lambda_layer/NOTES.md](lambda_layer/NOTES.md) on how to repair this.

If it says ``[SEVERE]: bind() failed: Cannot assign requested address (99)``, run with Selenium and inspect the ``chromedriver.log`` file. If it says ``[INFO]: listen on IPv6 failed with error ERR_ADDRESS_INVALID``), that's a red herring.

### Zombie processes

**Looks like:** Web driver or browser processes not being cleaned up after the program exits.

**Caused by:** Bad code.

**Resolve by:** Surround code blocks with ``try finally`` blocks and call ``webdatasource.py#quit_selenium()`` method.

## Thanks

Lambda implementation based on https://github.com/alixaxel/chrome-aws-lambda but ported to Python.

### HTML DOM source is different between browsers

Various reasons:

* Responsive websites may change their content based on the size of the view port. For Chrome this is set as a launch option but is not set for Firefox.
* Browser extensions and add-ons. The Firefox profile runs with a 'Selenium' profile with no extensions on Desktop since my default profile has NoScript installed and will likely break many sites