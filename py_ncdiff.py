#!/usr/bin/env python

"""
Python tool to compare netCDF files. Flag the following differences:
1. Variables that appear in one file but not the other
2. Variables with the same name that are not the same type in the two files
3. Variables with the same name that have different dimensions in the two files
4. Variables with the same name but different metadata in the two files
5. Variables with the same name but different values in the two files

Besides standard libraries, needs the following python packages:
* netCDF4
* xarray
"""

###################

def init_logging():
    """
    Setup logger so WARNINGS and ERRORS -> stderr, rest to stdout
    Taken from
    https://gist.github.com/timss/8f03ae681256f21e25f8b0a16327c26c
    which in turn is based on
    http://stackoverflow.com/a/24956305/1076493
    """

    import logging
    import sys

    class MaxLevelFilter(logging.Filter):
        def __init__(self, level):
            self.level = level

        def filter(self, record):
            return record.levelno < self.level

    # Initialize two log streams
    logging_out = logging.StreamHandler(sys.stdout)
    logging_err = logging.StreamHandler(sys.stderr)

    # Format warnings / errors differently than info
    logging_out.setFormatter(logging.Formatter('%(message)s'))
    logging_err.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    # Set levels / filters so standard output is >= DEBUG but < WARNING
    # and error output is >= WARNING
    logging_out.setLevel(logging.DEBUG)
    logging_out.addFilter(MaxLevelFilter(logging.WARNING))
    logging_err.setLevel(logging.WARNING)

    # Initialize logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging_out)
    logger.addHandler(logging_err)

##########

class netCDF_comp_class(object):
    """
    Class constructor reads netCDF via xarray; lots of comparison routines.
    """

    ###################

    def __init__(self, file1, file2):
        """
        Use xarray to read datasets (save as class objects)
        """
        import os
        import sys
        import logging
        import time

        logger = logging.getLogger(__name__)
        try:
            import xarray as xr
        except:
            logger.error('Can not import xarray')
            sys.exit(1)

        # Read file1
        if os.path.isfile(file1):
            self.ds1 = xr.open_dataset(file1, decode_times=False, decode_coords=False)
        else:
            logger.error('Can not open %s', file1)
            sys.exit(1)

        # Read file2
        if os.path.isfile(file2):
            self.ds2 = xr.open_dataset(file2, decode_times=False, decode_coords=False)
        else:
            logger.error('Can not open %s', file2)
            sys.exit(1)

        logger.info("Comparing %s and %s", file1, file2)
        logger.info("First file modified:  %s", time.ctime(os.path.getmtime(file1)))
        logger.info("Second file modified: %s", time.ctime(os.path.getmtime(file1)))

###################

def _parse_args():
    """ Parse command line arguments
    """

    import argparse

    parser = argparse.ArgumentParser(description="Compare two netCDF files; rel error is (file1-file2)/file1",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--file1', action='store', dest='file1',
                        help='First file to compare')

    parser.add_argument('--file2', action='store', dest='file2',
                        help='Second file to compare')

    parser.add_argument('--vars', nargs='+', action='store', dest='vars',
                        default=None, help="Specifc variables to compare (None => compare all)")

    return parser.parse_args()

###################

if __name__ == "__main__":
    # Parse command-line arguments (marbl_root is used to set default for JSON file location)
    args = _parse_args()
    init_logging()

    test=netCDF_comp_class(args.file1, args.file2)
