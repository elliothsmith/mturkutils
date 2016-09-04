# mturkutils - Experiments on MTurk

`mturkutils` is a Python library for generating high-throughput web-based human psychophysics experiments for the Amazon Mechanical Turk platform.

**Note:** this package has been implemented for the DiCarlo Lab and currently is not suited well for external usage.

## Installation

`pip install git+https://github.com/dicarlolab/mturkutils.git`

## Directory structure

- `mturkutils`: Python package to run and retrieve MTurk experiments
  - `lib`: All commonly used (web-related, mostly JavaScript) libraries
  - `tests`: Tests to make sure the package is working properly
- `experiments`: Actual experiment that people in the lab have built
- `scripts`: Command line interfaces common to all experiments
- `tutorials`: Learn how to use this package

## TO-DO

- Update to `boto3`
- Prepare an example for using `exp.py`

## License

TDB