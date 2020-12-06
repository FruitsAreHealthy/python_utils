from msvc_compiler.cpp_makebuild import *
from ospp.cd import cd
import subprocess

def run():
    dlls = {
    "dummyDll": {
            'sources': [
                '../test_scripts/dummy.cpp'
                ],
            'source_type' :           EXE,
            'include' :               [],
            'warningLevel' :          DEBUG_BUILD_WARNING_LEVEL,
            'compilerDefinitions' :   ['DEBUG',],
            'ignoreWarnings' :        DEBUG_BUILD_IGNORE_WARNINGS,
            'optimizationFlags' :     DEBUG_BUILD_OPTIMIZATION_FLAGS,
            'errorHandling' :         DEBUG_BUILD_ERROR_HANDLING,
            'debugging' :             DEBUG_BUILD_DEBUGGING,
            'externalLibs' :          DEBUG_BUILD_EXTERNAL_LIBS,
       }
    }
    dll = buildDll('dummyDll',EXE,dlls['dummyDll'])
    cmd = dll.build()
    # set working dir in test folder to output/find dlls
    module_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','cache'))
    print("Building dummyDll.exe in %s" % module_dir)
    with cd(module_dir):
        compiler = MSVCBuilder('dummy_msvc_database.sqlite3')
        compiler.addDll(dll)
        compiler.buildSolution()
        try:
            output = subprocess.check_output('dummyDll.exe',stderr=subprocess.STDOUT,shell=True)
            print("Calling dummyDll.exe..output:\n%s" % output.decode('ascii'))
        except subprocess.CalledProcessError as e:
            print(e.output.decode('ascii'))
            return False
    return True







