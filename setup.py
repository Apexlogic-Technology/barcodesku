from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

from barcodesku import __version__ as version

setup(
	name="barcodesku",
	version=version,
	description="Barcode and SKU Auto Generator for items in ERPNext",
	author="Apexlogic",
	author_email="hello@apexlogic.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
