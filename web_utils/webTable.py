from html.parser    import HTMLParser
from lxml           import html

#url = 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/table'
#url = 'https://software.intel.com/sites/landingpage/IntrinsicsGuide/'

class HTMLTable(object):
    def __init__(self,name):
        self.name = name
        self.data = []
        self.columns = 0
        self.rows = 0
        self.maxColLength = [] # max length each column

    def getSize(self,index):
        return ("%i R x %i C" % (self.rows,self.columns))

    def prettyTable(self):
        for r in range (0,self.rows):
            format_row = ''.join([("{:15.%i}" % (max(self.maxColLength[i],15))) for i in range(0,self.columns)])
            data = [c[r].replace('\n','') for c in self.data]
            print(format_row.format(*data))

class HTMLTableParser(HTMLParser):
    """
    Parses html to find all table elements and storages them into HTMLTable
    objects.
    @usage:
    import requests
    url = 'https://docs.microsoft.com/en-us/cpp/build/reference/compiler-options-listed-alphabetically?view=msvc-160'
    r = requests.get(url)
    if r.status_code == 200:
        p = HTMLTableParser()
        try:
            p.feed(r.text)
            print("%i tables found" % p.countTables)
            for t in p.tables:
                print(t.name)
                t.prettyTable()
        except Exception as e:
            print("%i tables found" % p.countTables)
            print("Row index '%i' from last table '%s'" % (p._table.rows, p._table.name))
            raise e
    else:
        print("Couldn't load page returns code %s" % r.status_code)
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self._recordingData   = 0
        self._recordingRow    = 0
        self._checkLength      = 0
        self.tables             = [] # HTMLTable
        self.countTables        = 0
        self._lastID           = ""

    def _currentColIndex(self):
        return self._recordingData - 1

    def _getActivecell(self):
        return self._table.data[self._recordingData -1][self._table.rows-1]
    def _setActivecell(self,value):
        self._table.data[self._recordingData -1][self._table.rows-1] = value

    @property
    def _table(self):
        if self.countTables == 0:
            raise Exception("Attempting to access table array before any table was added")
        return self.tables[self.countTables-1]

    def handle_starttag(self,tag,attrs):
        # record any ID. Table will be assigned latest ID found unless if table
        # has ID attribute
        attribID = [value for name,value in attrs if name=='id']
        if attribID:
            self._lastID = attribID
        if tag == 'table':
            self.tables.append(HTMLTable(self._lastID))
            self.countTables += 1
        if tag == 'tr':
            self._recordingRow = 1
            self._table.rows += 1
        if tag == 'td' and self._recordingRow:
            self._recordingData += 1
            self._checkLength = 0
            if self._recordingData > self._table.columns:
                self._table.columns += 1
                self._table.data.append(['']*self._table.rows)
                self._table.maxColLength.append(0)
            else:
                self._table.data[self._recordingData-1].append('')

    def handle_endtag(self,tag):
        if tag == 'tr':
            self._recordingRow = 0
            self._recordingData = 0
        if tag == 'td':
            if self._table.maxColLength[self._currentColIndex()] < len(self._getActivecell()):
                self._table.maxColLength[self._currentColIndex()] = len(self._getActivecell())

    def handle_data(self,data):
        if self._recordingData:
            colIndex = self._recordingData - 1 #base
            self._table.data[colIndex][self._table.rows-1] += data

    def getTables(self):
        return [t.name for t in self.tables]

