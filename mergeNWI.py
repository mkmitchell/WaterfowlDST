"""
mergeNWI
========
mergeNWI is an example of how to merge NWI given a geodatabase and wildcard
"""

import os, sys, getopt, datetime, logging, arcpy, re
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
    for opt, arg in opts:
      if opt in ('-g', '--geodatabase'):
         gdb = arg
         arcpy.env.workspace = gdb
      elif opt in ("-w", "--wildcard"):
          wld = arg

    # Get and print a list of tables
    tables = arcpy.ListTables(wld)
    tblarr = []
    for table in tables:
        print(table)
        tblarr.append(table)
        if arcpy.ListFields(table, "CLASS"):  
            print("Field exists")
        else:  
            print("Field doesn't exist")
            arcpy.AddField_management(table, "CLASS", "TEXT")
        toClass = re.split("\w\w\w\w", table, 1)[1]
        arcpy.CalculateFields_management(table, "PYTHON3", [["CLASS", '"' + toClass+'"']])

    arcpy.Merge_management(tblarr, "MergedNWI")
    print('Done')

if __name__ == "__main__":
    print('\nRunning merge')
    print('#####################################\n')
    main(sys.argv[1:])    