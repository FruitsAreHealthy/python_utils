import  os
import  sqlite3
import  datetime
import  subprocess
from    msvc_compiler import msvc

DLL = 'DLL'
EXE = 'EXE'
SOURCE_TYPES = {
            'DLL': DLL,
            'EXE': EXE
        }

DEBUG_BUILD_OPTIMIZATION_FLAGS  = r'/Od /Oi'
DEBUG_BUILD_ERROR_HANDLING      = r'/EHa'
DEBUG_BUILD_DEBUGGING           = r'/Zi'

DEBUG_BUILD_WARNING_LEVEL       = r'-Wall -WX' 
DEBUG_BUILD_IGNORE_WARNINGS = { 
        '4255','4100','4101','4710','4127',
        '4820','4061','4464','4840','4668',
        '4201','5045','4339','4514','4189'
        }

# win32 libs
DEBUG_BUILD_EXTERNAL_LIBS = {
        'user32.lib',
        'gdi32.lib',
        'opengl32.lib',
        'Shell32.lib',
        'kernel32.lib',
        'vcruntime.lib',
        'msvcrt.lib',
        } 

class MSVCBuilder(object):
    """ Maintains file database with build status """
    dlls = {}
    conn = None
    dirty = set()
    # list of tables with columns [name,type,allow nulls]
    tablesDef = {
            'FileUpdates' : [
                    ['dll','text','not null'],
                    ['name','text','not null'],
                    ['lastUpdated','interger','not null'],
                ],
            'DllBuilt' : [
                    ['dll','text','not null'],
                    ['success','integer','not null'],
                    ['err_msg','text','null'],
                ]
            }
    def __init__(self, fileTracker,reset=False):
        super(MSVCBuilder, self).__init__()
        self.fileTracker = fileTracker
        if reset:
            if os.path.exists(fileTracker):
                os.remove(fileTracker)
        self.conn = sqlite3.connect(fileTracker) 
        self.__startDB()
        self.__cursor = None

    def close(self):
        self.conn.close()

    @property
    def _cursor(self):
        if self.__cursor is None:
            self.__cursor = self.conn.cursor()
        return self.__cursor

    @_cursor.setter
    def _cursor(self,value):
        self.__cursor = value

    # QUERIES
    # DOES NOT AUTO COMMIT #
    def _tableExists(self,name):
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(name,))
        return (not self._cursor.fetchone() is None)
    def _insertNewFile(self,dll,filename,lastUpdated):
        self._cursor.execute("INSERT INTO FileUpdates (dll,name,lastUpdated) VALUES (?,?,?)",(dll,filename,lastUpdated))
    def _dllSourceFilesLastUpdated(self,dll):
        self._cursor.execute("SELECT name,datetime(lastUpdated,'unixepoch') FROM FileUpdates WHERE dll=?",(dll,))
        return self._cursor.fetchall()
    def _removeSource(self, dll ,fileRemoved):
        self._cursor.execute("DELETE FROM FileUpdates WHERE dll=? and name=?",(dll,fileRemoved))

    # success == 0
    # fails != 0 (where will be error msg)
    def _buildResult(self,dll,success, err_msg):
        self._cursor.execute("DELETE FROM DllBuilt where dll=(?)",(dll,))
        self._cursor.execute("INSERT INTO DllBuilt (dll,success,err_msg) values(?,?,?)",(dll,success,err_msg))
        #self._cursor.execute("
    
    def buildErrors(self):
        self._cursor.execute("SELECT * FROM DllBuilt WHERE success != 0")
        errors = self._cursor.fetchall()
        return errors

    def printBuildErrors(self):
        errors = self.buildErrors()
        for e in errors:
            print("While building %s following errors occurred:\n%s" % (e[0], e[2].decode('ascii')))

    def __startDB(self):
        self._cursor = self.conn.cursor()
        for name,columns in self.tablesDef.items():
            if not self._tableExists(name):
                sqlColumns = ', '.join([' '.join(statement) for statement in columns])
                cmd = "CREATE TABLE %s (%s)" % (name,sqlColumns)
                self._cursor.execute(cmd)
        self.conn.commit()

    """
    check if exists in db and if date last update matches against file last
    modified. Otherwise write it as dirty file, force recompilation
    """
    def addDll(self,dll):
        self.dlls[dll.name] = dll
        dllRegFiles = self._dllSourceFilesLastUpdated(dll.name)
        for f in dll.files:
            found = os.path.isfile(f)
            if not found:
                raise OSError(2,"'%s' .c/cpp file for dll '%s' does not exists" % (f,dll.name))
            lastUpdated = os.path.getmtime(f)
            # new source file?
            dllFileRow = [dllFile for dllFile in dllRegFiles if f in dllFile[0]]
            if len(dllFileRow) == 0:
                self._insertNewFile(dll.name,f,lastUpdated)
                self.dirty.add(f)
            else:
                name,dbLastUpdated = dllFileRow[0]
                utc_time = datetime.datetime.strptime(dbLastUpdated,"%Y-%m-%d %H:%M:%S")
                dbLastUpdated = int((utc_time- datetime.datetime(1970,1,1)).total_seconds())
                if dbLastUpdated < int(lastUpdated):
                    self._removeSource(dll.name,f)
                    self._insertNewFile(dll.name,f,lastUpdated)
                    self.dirty.add(name)
        for fileInDb in dllRegFiles:
            file_name = fileInDb[0]
            if not file_name in dll.files:
                self._removeSource(dll.name,fileRemoved)
        self.conn.commit()

    def fileIsDirty(self,name):
        return name in self.dirty

    def buildSolution(self):
        rebuild = {}
        buildErrors = [err[0] for err in self.buildErrors()]
        for name,dll in self.dlls.items():
            if name in buildErrors:
                rebuild[name] = dll
            else:
                for f in dll.files:
                    if self.fileIsDirty(f):
                       rebuild[name] = dll
                       break
        for name,dll in rebuild.items():
            print("%s dll needs recompilation" % name)
            cmd = dll.build()
            try:
                output = subprocess.check_output(cmd,stderr=subprocess.STDOUT,shell=True)
            except subprocess.CalledProcessError as e:
                print(e.output.decode('ascii'))
                self._buildResult(name,e.returncode,e.output)
            else:
                self._buildResult(name,0,cmd)
        if len(rebuild) > 0:
            self.conn.commit()
        else:
            print("No changes in source files")


class DllBuilder(object):
    """docstring for DllBuilder"""
    name = ""
    files = []
    include = ""
    compilerDefinitions=[]
    warningLevel=""
    ignoreWarnings=[]
    optimizationFlags=""
    errorHandling=""
    debugging= ""
    externalLibs=[]
    
    def __str__(self):
        return "Dll %s" % self.name

    def __init__(self, name,source_type,
                       files,
                       include,
                       compilerDefinitions=[],
                       warningLevel='-Wall -WX',
                       ignoreWarnings=[],
                       optimizationFlags=r'/Od /Oi',
                       errorHandling=r'/EHa',
                       debugging=r'/Zi',
                       externalLibs=[]):
        super(DllBuilder, self).__init__()
        self.name = name
        if not source_type in ('EXE','DLL'):
            raise Exception("source_type must be either DLL or EXE")
        self.source_type = source_type
        if (type(files) is str):
            files = {files}
        self.files = files
        self.include = include
        self.compilerDefinitions = compilerDefinitions
        self.warningLevel = warningLevel
        self.ignoreWarnings = ignoreWarnings
        self.optimizationFlags = optimizationFlags
        self.errorHandling = errorHandling
        self.debugging = debugging
        self.externalLibs = externalLibs

    def hasChanged(self):
        for f in self.files:
            print(f)
        return True

    def build(self,checkIfChanges=False):
        msvc.StartVisualStudioEnvVars()
        if checkIfChanges:
            if not self.hasChanged():
                return
        # make list append dummy value at beginning to join members like -Dmember1 -Dmember2
        compilerDefinitions = list(self.compilerDefinitions)
        compilerDefinitions.insert(0,'')
        include = list(self.include)
        include.insert(0,'')
        ignoreWarnings = list(self.ignoreWarnings)
        ignoreWarnings.insert(0,'')
        cmd = (
                f"cl /nologo %s %s %s %s %s %s %s %s %s /link %s -opt:ref %s %s /NODEFAULTLIB:LIBCMT" % (
                                        ' -D'.join(compilerDefinitions),
                                        self.warningLevel,
                                        ' -wd'.join(ignoreWarnings),
                                        self.optimizationFlags,
                                        self.errorHandling,
                                        self.debugging,
                                        ' /I '.join(include),
                                        ' '.join(self.files),
                                        ' -LD' if self.source_type == 'DLL' else '',
                                        ' -OUT:' + self.name + ('.dll' if self.source_type == 'DLL' else '.exe'),
                                        ' -IMPLIB:' + self.name + '.lib' if self.source_type == 'DLL' else '',
                                        ' '.join(self.externalLibs)
                                        )
            )
        return cmd

def buildDll(name,source_type,kw):
     dll = DllBuilder(name,source_type,
                      kw['sources'],kw['include'],
                      kw['compilerDefinitions'],
                      kw['warningLevel'],
                      kw['ignoreWarnings'],
                      kw['optimizationFlags'],
                      kw['errorHandling'],
                      kw['debugging'],
                      kw['externalLibs'])
     return dll


