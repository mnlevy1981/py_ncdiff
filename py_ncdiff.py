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
import logging

###################

def init_logging():
    """
    Setup logger so WARNINGS and ERRORS -> stderr, rest to stdout
    Taken from
    https://gist.github.com/timss/8f03ae681256f21e25f8b0a16327c26c
    which in turn is based on
    http://stackoverflow.com/a/24956305/1076493
    """
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

    def __init__(self, baseline, new_file, quiet=False):
        """
        Use xarray to read datasets (save as class objects)
        """
        import os
        import sys
        import time
        from collections import OrderedDict

        logger = logging.getLogger(__name__)
        try:
            import xarray as xr
        except:
            logger.error('Can not import xarray')
            sys.exit(1)

        # Set up dictionaries to store datasets / metadata about datasets and also test results
        self.baseline = dict()
        self.new_file = dict()
        self.quiet = quiet
        self.test_results = OrderedDict()

        # Read baseline
        if os.path.isfile(baseline):
            self.baseline['ds'] = xr.open_dataset(baseline, decode_times=False, decode_coords=False)
            self.baseline['vars'] = self.baseline['ds'].variables.keys()
        else:
            logger.error('Can not open %s', baseline)
            sys.exit(1)

        # Read new_file
        if os.path.isfile(new_file):
            self.new_file['ds'] = xr.open_dataset(new_file, decode_times=False, decode_coords=False)
            self.new_file['vars'] = self.new_file['ds'].variables.keys()
        else:
            logger.error('Can not open %s', new_file)
            sys.exit(1)

        # Make list of variables that appear in both
        self.common_vars = list(set(self.baseline['vars']) & set(self.new_file['vars']))

        logger.info("Comparing %s and %s\n-----", baseline, new_file)
        logger.info("Baseline modified: %s", time.ctime(os.path.getmtime(baseline)))
        logger.info("New file modified: %s", time.ctime(os.path.getmtime(new_file)))
        logger.info("-----")

    ###################

    def compare_variable_names(self):
        """
        PASS if all variables in baseline are also in new_file and vice versa
        FAIL if any variable is in baseline but not new_file or vice versa
        """
        logger = logging.getLogger(__name__)
        test_desc = 'Compare Variable Names'
        if not self.common_vars:
            logger.info("%s: no variables to test!", test_desc)
            return
        self.test_results[test_desc] = dict()

        # Lists are identical if self.baseline['vars'], self.new_file['vars'], and self.common_vars
        # are all the same length
        if ((len(self.baseline['vars']) == len(self.new_file['vars'])) and
            (len(self.baseline['vars']) == len(self.common_vars))):
            self.test_results[test_desc]["result"] = "Variable list matches -- all variables exist in both files"
            self.test_results[test_desc]["pass"] = True
            return

        # Create lists of variables in one file but not the other
        baseline_only = [var for var in self.baseline['vars'] if var not in self.common_vars]
        new_file_only = [var for var in self.new_file['vars'] if var not in self.common_vars]

        # Variable lists do not match!
        # Log data unless run with --quiet
        if not self.quiet:
            # Log the contents of these lists
            if baseline_only:
                logger.info("%d variable(s) are in the baseline but not the new file:", len(baseline_only))
                for n, var in enumerate(baseline_only):
                    logger.info("%d. %s", n+1, var)
            if new_file_only:
                logger.info("%d variable(s) are in the new file but not the baseline:", len(new_file_only))
                for n, var in enumerate(new_file_only):
                    logger.info("%d. %s", n+1, var)
            logger.info("")
        # Store test results
        success_cnt = len(self.common_vars)
        fail_cnt = len(baseline_only) + len(new_file_only)
        self.test_results[test_desc]["result"] = "Variable list does not match -- %d variables exist in one file but not the other, only %d in both" % \
            (fail_cnt, success_cnt)
        self.test_results[test_desc]["pass"] = False
        self.test_results[test_desc]["fail_msg"] = "%d/%d pass" % (success_cnt, success_cnt + fail_cnt)

    ###################

    def compare_variable_type_and_dims(self):
        """
        For variables defined in both files, check the following:
        1. Are the variables the same type in both files?
        2. Are the variables the same dimensions in both files?
        """
        logger = logging.getLogger(__name__)
        test_desc = 'Compare Variable Types and Dimensions'

        if not self.common_vars:
            logger.info("%s: no variables to test!", test_desc)
            return
        self.test_results[test_desc] = dict()
        self.test_results[test_desc]["pass"] = True

        remove_var = []
        for var in self.common_vars:
            # # Using numpy.equals() is speedy-ish
            # if not self.baseline['ds'][var].equals(self.new_file['ds'][var]):
            #     remove_var.append(var)
            #     if not self.quiet:
            #         logger.info("Variable %s is not the same between files", var)
            # Look for variables that differ in type
            if self.baseline['ds'][var].dtype != self.new_file['ds'][var].dtype:
                remove_var.append(var)
                # self.baseline['ds'].drop(var)
                # self.new_file['ds'].drop(var)
                if not self.quiet:
                    logger.info("%s is type %s in baseline and type %s in new file", var,
                                self.baseline['ds'][var].dtype, self.new_file['ds'][var].dtype)
            # Look for variables that differ in number of dimensions
            elif self.baseline['ds'][var].ndim != self.new_file['ds'][var].ndim:
                remove_var.append(var)
                # self.baseline['ds'].drop(var)
                # self.new_file['ds'].drop(var)
                if not self.quiet:
                    logger.info("%s has %d dimensions in baseline and %d dimensions in new file", var,
                                self.baseline['ds'][var].ndim, self.new_file['ds'][var].ndim)
            # Look for variables that differ in size
            elif self.baseline['ds'][var].sizes != self.new_file['ds'][var].sizes:
                remove_var.append(var)
                # self.baseline['ds'].drop(var)
                # self.new_file['ds'].drop(var)
                if not self.quiet:
                    logger.info("%s has size %d in baseline and size %d in new file", var,
                                self.baseline['ds'][var].size, self.new_file['ds'][var].size)

        # Remove variables that differ in type from common_vars
        total_cnt = len(self.common_vars)
        if remove_var:
            self.test_results[test_desc]["pass"] = False
            for var in remove_var:
                self.common_vars.remove(var)
            fail_cnt = len(remove_var)
            self.test_results[test_desc]["fail_msg"] = "%d/%d pass" % (total_cnt - fail_cnt, total_cnt)
            self.test_results[test_desc]["result"] = "Variable types / dimensions do not match -- " + \
                "%d of %d variables that appear in both files differ in type or dimension" % \
                (fail_cnt, total_cnt)
        else:
            self.test_results[test_desc]["result"] = "All %d variables that appear in both files have same type / dimension" % \
                total_cnt

    ###################

    def parse_results(self):
        """
        Summarize test results
        """
        logger = logging.getLogger(__name__)
        fail_cnt = 0
        for n, test_desc in enumerate(self.test_results.keys()):
            # Increment fail count
            if not self.test_results[test_desc]["pass"]:
                fail_cnt += 1
            if self.quiet:
                if self.test_results[test_desc]["pass"]:
                    results = test_desc + ": PASS"
                else:
                    results = "%s: FAIL (%s)" % (test_desc, self.test_results[test_desc]["fail_msg"])
            else:
                results = self.test_results[test_desc]["result"]
            logger.info("(%d) %s", n+1, results)
        return fail_cnt

###################

def _parse_args():
    """ Parse command line arguments
    """

    import argparse

    parser = argparse.ArgumentParser(description="Compare two netCDF files; rel error is (baseline-new_file)/baseline",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--baseline', action='store', dest='baseline', required=True,
                        help='Baseline (file to be compared against)')

    parser.add_argument('--new_file', action='store', dest='new_file', required=True,
                        help='New file (file to compare to baseline)')

    parser.add_argument('-q', '--quiet', action='store_true', dest='quiet',
                        help="Very simple output")

    parser.add_argument('--vars', nargs='+', action='store', dest='vars',
                        default=None, help="Specific variables to compare (None => compare all)")

    return parser.parse_args()

###################

if __name__ == "__main__":
    import sys
    # Parse command-line arguments (marbl_root is used to set default for JSON file location)
    args = _parse_args()
    init_logging()
    logger = logging.getLogger(__name__)

    test=netCDF_comp_class(args.baseline, args.new_file, args.quiet)
    test.compare_variable_names()
    test.compare_variable_type_and_dims()

    # Summary (requires test and error counts)
    err_cnt = 0
    test_cnt = 0
    logger.info("Summary\n-------")
    err_cnt = test.parse_results()

    sys.exit(err_cnt)
