# Lambda Layer

This page describes combinations of browsers and web drivers.

## Introduction

### Working combinations

The automated web testing ecosystem is fragile. It is highly sensitive to versions of:

1. the browser itself
1. the web driver (i.e. GeckoDriver for Firefox, ChromeDriver for Chromium/Chrome)
1. Selenium

The following combos have been verified:

**On Windows 10**

* Selenium 4.5.0, Chrome  106.0.5249.119 (x64), ChromeDriver 106.0.5249.61 (x64)
* Selenium 4.5.0, Firefox 105.0.3 (x64), GeckoDriver 0.32.0 (x64)
* Selenium 3.141.0, Chrome 90.0.4430.24 (x64), ChromeDriver 90.0.4430.24 (x64)
* Selenium 3.141.0, Firefox 88.0 (x64), GeckoDriver 0.29.1 (x64)

**On Amazon Linux 2 (EC2 instance)**

* Selenium 4.5.0, alixaxel Chromium 92.0.4512.0, ChromeDriver 92.0.4515.107 (x64)
* Selenium 3.141.0, alixaxel Chromium 80.0.3987.0, ChromeDriver 80.0.3987.106 (x64)

**On AWS Lambda (some custom AMI AWS doesn't publish)**

* Selenium 3.141.0, alixaxel Chromium 90.0.4430.24, ChromeDriver 90.0.4430.24 (x64)

	* this NPM module has special code to munge the ``.so*`` onto the ``LD_LIBRARY_PATH``

### Where to download artifacts from

* Chrome:
	* use regular [Chrome](https://www.google.com/chrome/) on Windows
	* use alixaxel Chromium from the [chrome-aws-lambda](https://github.com/alixaxel/chrome-aws-lambda) NPM module (see instructions below)
* [ChromeDriver](https://chromedriver.chromium.org/downloads) to be used with Chrome
* Firefox
	* use regular [Firefox](https://www.mozilla.org/en-US/firefox/new/) on Windows
	* no verified Firefox version works on Linux :(
* [GeckoDriver](https://github.com/mozilla/geckodriver/releases) to be used with Firefox


## Prepare The Lambda Layer

Currently:

* This Lambda layer assumes alixaxel Chromium with ChromeDriver is being used as this is the only verified combination to work on Lambda.
* Only the hard-to-get ``.so*`` libraries (see below) are committed to git. The rest of the files need to be downloaded and extracted.

### Expected structure

```
lambda_layer
	├── aws
	│   ├── fonts.conf
	│   └── lib
	│       ├── libX11-xcb.so.1.0.0
	│       ├── libX11.so.6.3.0
	│       ├── libXau.so.6.0.0
	│       ├── libexpat.so.1
	│       ├── libglib-2.0.so.0.5600.1
	│       ├── libnss3.so
	│       ├── libnssutil3.so
	│       ├── libsoftokn3.so
	│       ├── libsqlite3.so.0
	│       ├── libuuid.so.1
	│       └── libxcb.so.1.1.0
	├── chromedriver
	│   └── chromedriver
	├── chromium
	│   ├── chromium
	│   └── swiftshader
	│       ├── libEGL.so
	│       └── libGLESv2.so
	├── NOTES.md
```

To create this:

1. Download Linux x64 ChromeDriver and extract into ``lambda_layer/chromedriver/``
1. Download the [chrome-aws-lambda](https://github.com/alixaxel/chrome-aws-lambda) NPM module version 10.1.0 (easiest way is to hit the NPM registry [directly](https://registry.npmjs.org/chrome-aws-lambda/-/chrome-aws-lambda-10.1.0.tgz)) and copy into the ``lambda_layer`` directory as follows:
    1. Brotli decompress the files in the ``package/bin/`` directory (there's a ``brotli`` apt module for this)
    1. Extract decompressed ``package/bin/aws`` directory into ``lambda_layer``
    1. Extract decompressed ``package/bin/chromium`` file into ``lambda_layer``
    1. Extract decompressed ``package/bin/swiftshader`` directory into ``lambda_layer/chromium/swiftshader``

If the hard-to-get ``.so*`` files libraries need to be retrieved again:

1. Start a Amazon Linux 2 AMI (note this isn't perfect as Lambda uses a custom AMI)
1. ``sudo yum update`` to get the latest packages
1. ``sudo yum install`` the library if it isn't already installed

	* ``sudo yum whatprovides "*/libglib*"`` is useful to determine the yum package based on a file within it
	* ``sudo rpm -ql libX11`` shows what files the package (libX11 in this case) provides

1. Copy the ``.so*`` files into ``lambda_layer/aws/lib``
1. For symlinks, update ``lambda_layer.py`` to create them

### Publishing to Lambda

1. Build the Lambda layer zip package using top-level Ant build file

	```
	$ ant layer
	```

1. Publish the layer to AWS S3 (it's too big to upload directly to Lambda)

	Note the ``ant layer.publish`` target does this step for you.

	```
	$ aws s3 cp build/selenium_chromium_layer.zip s3://my-cloudformation-bucket-ap-southeast-2/priceperformancechart/layer/ --region ap-southeast-2

	$ aws lambda publish-layer-version --layer-name selenium_chromium --description "Headless Chromium for Selenium" --content S3Bucket=my-cloudformation-bucket-ap-southeast-2,S3Key=priceperformancechart/layer/selenium_chromium_layer.zip --region ap-southeast-2
	```

1. Update the CloudFormation template to reference the layer's new ARN (which includes version information)
