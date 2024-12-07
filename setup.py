from setuptools import setup

setup(name='cbpi4-pressure-i2c',
      version='0.0.2',
      description='Pressure Sensor i2c with tca9548A and two ADS1115',
      author='Max Sidenstjärna',
      author_email='',
      url='',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4-pressure-i2c': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4-pressure-i2c'],
     )
