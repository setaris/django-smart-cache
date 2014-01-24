from setuptools import setup, find_packages


install_requires = [
    'django >= 1.4',
]

setup(
    name = "django-smart-cache",
    version = '0.2',
    description = "A Django library that allows flexible database caching" +
        " using composite caching keys.",
    url = "https://github.com/setaris/django-smart-cache",
    author = "Setaris",
    author_email = "support@setaris.com",
    packages = find_packages(),
    install_requires = install_requires,
)