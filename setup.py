from setuptools import setup, find_packages

README = 'a distributed lock based on consul'
tests_require = [
    'pytest',  # includes virtualenv
    'testix',
    ]


requires = [ 'python-consul2', ]

setup(name='consulock',
      version='0.4.3',
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
        'testing': tests_require,
      },
      install_requires=requires,
      entry_points={
      },
      )
