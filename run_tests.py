import os,sys

modules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'libs')
sys.path.append(modules_path)

import test_scripts

for test in test_scripts.test_suite:
    print("------------------------------------------------")
    print("Running test %s" % test.__file__)
    print("------------------------------------------------")
    if not test.run():
        raise Exception("Failed running test")


