"""setuptools- and pip-enabled setup.py """

import logging
import os
import re
import codecs
import setuptools

# ----- overrides -----

# set these to anything but None to override the automatic defaults
version = None
packages = None
package_name = 'mturkutils'
package_data = None
scripts = None
requirements_file = None
requirements = ['numpy', 'scipy', 'boto', 'pymongo>=2.4.0', 'tabular', 'pandas']

# ----- control flags -----

# don't include subdir named 'tests' in package_data
skip_tests = True

# print some extra debugging info
debug = True

# -------------------------

here = os.path.abspath(os.path.dirname(__file__))

if debug:
    logging.basicConfig(level=logging.DEBUG)


def find_scripts():
    return [s for s in setuptools.findall('scripts/') \
            if os.path.splitext(s)[1] != '.pyc']


def package_to_path(package):
    """
    Convert a package (as found by setuptools.find_packages)
    e.g. "foo.bar" to usable path
    e.g. "foo/bar"

    No idea if this works on windows
    """
    return package.replace('.', '/')


def find_subdirectories(package):
    """
    Get the subdirectories within a package
    This will include resources (non-submodules) and submodules
    """
    try:
        subdirectories = os.walk(package_to_path(package)).next()[1]
    except StopIteration:
        subdirectories = []
    return subdirectories


def subdir_findall(dir, subdir):
    """
    Find all files in a subdirectory and return paths relative to dir

    This is similar to (and uses) setuptools.findall
    However, the paths returned are in the form needed for package_data
    """
    strip_n = len(dir.split('/'))
    path = '/'.join((dir, subdir))
    return ['/'.join(s.split('/')[strip_n:]) for s in setuptools.findall(path)]


def find_package_data(packages):
    """
    For a list of packages, find the package_data

    This function scans the subdirectories of a package and considers all
    non-submodule subdirectories as resources, including them in
    the package_data

    Returns a dictionary suitable for setup(package_data=<result>)
    """
    package_data = {}
    for package in packages:
        package_data[package] = []
        for subdir in find_subdirectories(package):
            if '.'.join((package, subdir)) in packages:  # skip submodules
                logging.debug("skipping submodule %s/%s" % (package, subdir))
                continue
            if skip_tests and (subdir == 'tests'):  # skip tests
                logging.debug("skipping tests %s/%s" % (package, subdir))
                continue
            package_data[package] += \
                    subdir_findall(package_to_path(package), subdir)
    return package_data


def parse_requirements(file_name):
    """
    from:
        http://cburgmer.posterous.com/pip-requirementstxt-and-setuppy
    """
    requirements = []
    with open(file_name, 'r') as f:
        for line in f:
            if re.match(r'(\s*#)|(\s*$)', line):
                continue
            if re.match(r'\s*-e\s+', line):
                requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$',\
                        r'\1', line).strip())
            elif re.match(r'\s*-f\s+', line):
                pass
            else:
                requirements.append(line.strip())
    return requirements


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


# ----------- Override defaults here ----------------

# Get the long description from the README file
long_description = read('README.md')

if packages is None:
    packages = setuptools.find_packages()

if len(packages) == 0:
    raise Exception("No valid packages found")

if version is None:
    version = find_version(package_name, '__init__.py')

if package_name is None:
    package_name = packages[0]

if package_data is None:
    package_data = find_package_data(packages)

if scripts is None:
    scripts = find_scripts()

if requirements_file is None:
    requirements_file = 'requirements.txt'

if os.path.exists(requirements_file):
    if requirements is None:
        requirements = parse_requirements(requirements_file)
else:
    if requirements is None:
        requirements = []

if debug:
    logging.debug("Module name: %s" % package_name)
    for package in packages:
        logging.debug("Package: %s" % package)
        logging.debug("\tData: %s" % str(package_data[package]))
    logging.debug("Scripts:")
    for script in scripts:
        logging.debug("\tScript: %s" % script)
    logging.debug("Requirements:")
    for req in requirements:
        logging.debug("\t%s" % req)

if __name__ == '__main__':

    sub_packages = packages

    setuptools.setup(
        name=package_name,
        version=version,
        long_description=long_description,
        url='https://github.com/dicarlolab/mturkutils',
        author='DiCarlo Lab',
        author_email='dlmug@mit.edu',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Science/Research',
            'Topic :: Scientific/Engineering',
            'Programming Language :: Python :: 2'
        ],
        keywords='mturk psychophysics',

        packages=packages,
        scripts=scripts,

        package_data=package_data,
        include_package_data=True,
        install_requires=requirements
    )