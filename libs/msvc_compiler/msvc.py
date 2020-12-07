from    web_utils   import webTable
import  os
from    copy        import copy
import  winreg
import  subprocess

KEYREG_VS = "SOFTWARE\Microsoft\VisualStudio\%s"
# does not exists but might eventually
VS_MAX_VERSION = 30
# this is a vs .bat to set all environment variables for cl.exe compilation
VS_DEFAULT_PATH_BAT = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat"

def _VisualStudioEnvVarsInPlace():
    return 'VisualStudioVersion' in os.environ

def StartVisualStudioEnvVars():
    if _VisualStudioEnvVarsInPlace():
       return
    try:
        temp_file = 'cache/temp_file.txt'
        if not os.path.exists(temp_file):
            cmd = '"%s" %s && set > %s' % (VS_DEFAULT_PATH_BAT,"x64",temp_file)
            output = subprocess.check_output(cmd,stderr=subprocess.STDOUT,shell=False)
            print(output.decode('ascii'))
        with open(temp_file,'r') as fp:
            for line in fp.read().splitlines():
                kv = line.split('=',1)
                os.environ[kv[0]] = kv[1]
    except subprocess.CalledProcessError as e:
        print(e.output.decode('ascii'))

def hasVisualStudio():
    available_vs = []

    for i in range(10,VS_MAX_VERSION):
        version = (KEYREG_VS % ("%i.0" % i))
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, version, 0, winreg.KEY_READ) as key:
                available_vs.append("%i.0" %i)
        except Exception as e:
            pass
    return available_vs

CACHE = os.path.join('cache','webparser_cache')

_htmlparser = webTable.HTMLTableParser()
_htmlparser.setCache(CACHE)

URLS = [
        'https://docs.microsoft.com/en-us/cpp/error-messages/compiler-warnings/compiler-warnings-c4000-through-c4199?view=msvc-160',
        'https://docs.microsoft.com/en-us/cpp/error-messages/compiler-warnings/compiler-warnings-c4200-through-c4399?view=msvc-160',
        'https://docs.microsoft.com/en-us/cpp/error-messages/compiler-warnings/compiler-warnings-c4400-through-c4599?view=msvc-160',
        'https://docs.microsoft.com/en-us/cpp/error-messages/compiler-warnings/compiler-warnings-c4600-through-c4799?view=msvc-160',
        'https://docs.microsoft.com/en-us/cpp/error-messages/compiler-warnings/compiler-warnings-c4800-through-c4999?view=msvc-160',
        'https://docs.microsoft.com/en-us/cpp/build/reference/linker-options?view=msvc-160',
        ]


try:
    for url in URLS:
        _htmlparser.feed(url)
except Exception as e:
    #print("%i tables found" % p.countTables)
    #print("Row index '%i' from last table '%s'" % (p._table.rows, p._table.name))
    raise e


def compilerFlags():
    t = _htmlparser.getTable('linker-options-listed-alphabetically')[0]
    t.prettyTable()

def printTables():
    for t in _htmlparser.tables:
        print(t.name)

def getWarningMessage(warningsToCheck):
    descriptions = {}
    if type(warningsToCheck) is str:
        warnings = [warningsToCheck]
    else:
        warnings = copy(warningsToCheck)
    tables = _htmlparser.getTable('warning-messages')
    for t in tables:
        for i in range(0,t.rows):
            w = t.data[0][i] 
            found = False
            for iw in warnings:
                if iw in w:
                    found = True
                    break
            if found:
                warnings.remove(iw)
                descriptions[iw] = t.data[1][i]
            if len(warnings) == 0:
                break
    return descriptions

