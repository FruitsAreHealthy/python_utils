from html.parser    import HTMLParser
from lxml           import html
import os
import json
import requests

#url = 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/table'
#url = 'https://software.intel.com/sites/landingpage/IntrinsicsGuide/'

class HTMLTable(object):
    def __init__(self,name):
        self.name = name
        self.data = []

    def getSize(self,index):
        return ("%i R x %i C" % (self.rows,self.columns))

    def maxColLength(self,columnIndex):
        maxsize = 0
        for s in self.data[columnIndex]:
            if len(s) > maxsize:
                maxsize = len(s)
        return maxsize

    @property
    def rows(self):
        if len(self.data) == 0:
            return 0
        return len(self.data[0])
    @property
    def columns(self):
        return len(self.data)
        
    def prettyTable(self):
        for r in range (0,self.rows):
            format_row = ''.join([("{:15.%i}" % (max(self.maxColLength(i),15))) for i in range(0,self.columns)])
            data = [c[r].replace('\n','') for c in self.data]
            print(format_row.format(*data))

class HTMLTableParser(HTMLParser):
    """
    Parses html to find all table elements and storages them into HTMLTable
    objects.
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self._recordingTable = 0
        self._recordingData = 0
        self._recordingRow  = 0
        self._checkLength   = 0
        self.tables         = [] # HTMLTable
        self._lastID        = ""
        self._cache         = None

    def _currentColIndex(self):
        return self._recordingData - 1

    def _getActivecell(self):
        return self._table.data[self._recordingData -1][self._table.rows-1]
    def _setActivecell(self,value):
        self._table.data[self._recordingData -1][self._table.rows-1] = value

    @property
    def countTables(self):
        return len(self.tables)

    @property
    def _table(self):
        if self.countTables == 0:
            raise Exception("Attempting to access table array before any table was added")
        return self.tables[self.countTables-1]

    """ 
    overwrite parser feed mechanism to pass small chunks. This is now to
    process entire content and hard reset. Save url for cache option
    !! set cache before feeding else will not check for it
    """
    def feed(self,url):
        if len(url) == 0:
            raise Exception("url can't be empty string")
        if self._cache:
            if self._urlPathExists(self._cache,url):
                self._loadFromCache(self._cache,url)
                return
        r = requests.get(url)
        if r.status_code != 200:
            raise Exception("http response returned status code %i (Only 200 is accepted)" % r.status_code)
        data = r.text
        super(HTMLTableParser,self).reset()
        self._url = url
        super(HTMLTableParser,self).feed(data)

    def handle_starttag(self,tag,attrs):
        # record any ID. Table will be assigned latest ID found unless if table
        # has ID attribute
        attribID = [value for name,value in attrs if name=='id']
        if attribID and not self._recordingTable:
            self._lastID = attribID[0]
        if tag == 'table':
            self._recordingTable = 1
            self.tables.append(HTMLTable(self._lastID))
        if self._recordingTable:
            if tag == 'tr':
                self._recordingRow = 1
            if tag == 'td' and self._recordingRow:
                self._recordingData += 1
                self._checkLength = 0
                if self._recordingData > self._table.columns:
                    self._table.data.append(['']*self._table.rows)
                self._table.data[self._recordingData-1].append('')

    def _loadFromCache(self,root,url):
        if not self._cache:
            raise AssertionError("Calling load from cache when cache is not set")
        path = self._getUrlCache(url)
        if not os.path.exists(path):
            raise IOError("Path ulr does not exists and requested cache (%s)" % path)
        files = os.listdir(path)
        for f in files:
            table = HTMLTable(f)
            js = None
            fullname = os.path.join(path,f)
            with open(fullname,'r') as fp:
                js = json.load(fp)
            table.data = js
            self.tables.append(table)

    def _urlToPath(self,url):
        return url.replace('\\','_').replace('/','_').replace(':','_').replace('?','_').replace('=','_')

    def _getUrlCache(self,url,create_if_missing=False):
        url_sanitized = self._urlToPath(url)
        path = os.path.join(os.path.abspath(self._cache),url_sanitized)
        if create_if_missing and not os.path.exists(path):
            os.makedirs(path,exist_ok=True)
        return path

    def _urlPathExists(self,root,url):
        url_sanitized = self._urlToPath(url)
        f = os.path.normpath(os.path.join(os.path.abspath(root),url_sanitized))
        return os.path.exists(f)

    def _sanitizePath(self,path,url,tableName):
        url_sanitized = self._urlToPath(url)
        f = os.path.normpath(os.path.join(os.path.abspath(path),url_sanitized))
        os.makedirs(f,exist_ok=True)
        f = os.path.join(f,tableName)
        return f

    def handle_endtag(self,tag):
        if self._recordingTable:
            if tag == 'tr':
                self._recordingRow = 0
                self._recordingData = 0
        if tag == 'table':
            self._recordingTable = 0
            if self._cache:
                path = self._getUrlCache(self._url,True)
                f = os.path.join(path,self._table.name)
                with open(f,'w') as fp:
                    json.dump(self._table.data,fp)


    def handle_data(self,data):
        if self._recordingData:
            colIndex = self._recordingData - 1 #base
            self._table.data[colIndex][self._table.rows-1] += data

    def getTable(self,name):
        tables = [t for t in self.tables if t.name == name]
        if len(tables) == 0:
            return None
        else:
            return tables

    """ set cache before feeding """
    def setCache(self,path):
        os.makedirs(path, exist_ok=True)
        self._cache = path


