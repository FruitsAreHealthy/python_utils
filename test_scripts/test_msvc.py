from msvc_compiler.msvc import MSVC

def run():
    msvc = MSVC()
    for table in msvc.getTables():
        print(table.name)
    return True
