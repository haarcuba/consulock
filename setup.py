from setuptools import setup, find_packages

README = 'a distributed lock based on consul'

requires = [ 'python-consul', ]

setup(name='consulock',
      version='0.1.4',
      description=README,
      long_description=README,
      url='https://github.com/haarcuba/consulock',
      classifiers=[
          "Programming Language :: Python",
      ],
      author='Yoav Kleinberger',
      author_email='haarcuba@gmail.com',
      keywords='consul',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      extras_require={
      },
      install_requires=requires,
      entry_points={
      },
      )
