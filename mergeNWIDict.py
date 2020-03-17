"""
mergeNWI
========
mergeNWI is an example of how to merge NWI given a geodatabase and wildcard
"""

import os, sys, getopt, datetime, logging, arcpy, re, json
import waterfowlmodel.mergeTable as mergeTable


def main(argv):
    """
    Runs mergeTable

    :param geodatabase: Geodatabase with tables.
    :type workspace: str
    :param wildcard: Wildcard all tables to be merged start with
    :type geodatabase: str 
    """
    opts, args = getopt.getopt(argv,"g:w:",["geodatabase=", "wildcard="])
    gdb = ''
    for opt, arg in opts:
      if opt in ('-g', '--geodatabase'):
         gdb = arg
         arcpy.env.workspace = gdb
      elif opt in ("-w", "--wildcard"):
          wld = arg

    # Get and print a list of tables
    tables = arcpy.ListTables(wld)
    tblDict = {}
    for table in tables:
        print(table)
        toClass = re.split("\w\w\w\w", table, 1)[1]
        if toClass not in tblDict:
            tblDict[toClass] = []
        cursor = arcpy.SearchCursor(table, fields='ATTRIBUTE')
        for row in cursor:
            tblDict[toClass].append(row.getValue('ATTRIBUTE'))

    print(tblDict.keys())
    json.dump( tblDict, open(os.path.join(os.path.dirname(gdb),"aoiWetland.json"), 'w' ))

    print('Done')

if __name__ == "__main__":
    print('\nRunning merge')
    print('#####################################\n')
    main(sys.argv[1:])    