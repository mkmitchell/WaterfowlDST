"""
runModel is an example of how to utilize the waterfowlmodel module.
"""

import os, sys, getopt, datetime, logging

def printHelp():
        """
        Prints information on how to call this python application from command line
        """
        print('\n finaloutput.py -r <Area of interest feature class> -w <workspace folder where geodatabases should reside> -g <geodatabase name>\n\n' \
                '\n This is the main python script for running the wintering grounds waterfowl model for both the Mississippi Alluvial Valley and West Gulf Coastal Plain regions.\n'\
                'It was written in python using the arcgis python libraries.  Initially it used ArcModels but they proved a bit limiting and not stable enough for future use.\n\n'\
                '\nusage: waterfowlmodel \t[--help] [--region <region>] \n'\
                '\t\t\t[--workspace <path>] [--geodatabase <geodatabase>] \n\n' \
                'These are the options used to initiate and run the waterfowl model properly.\n\n' \
                'Region\n' \
                '\t mav\t\t This option sets the model up to run the Mississippi Alluvial Valley region as the area of interest\n' \
                '\t wgcp\t\t This option sets the model up to run the West Gulf Coastal Plain region as the area of interest\n\n' \
                'Workspace\t\t The folder location where your geodatabase and scratch geodatabase will be write/read to/from\n' \
                'Geodatabase\t\t The geodatabase name where your input datasets will be read from and final output written to\n\n' \
                'Example:\n' \
                'finaloutput.py -r mav -w c:\intputfolder -g modelgeodatabase.gdb\n')
        sys.exit(2)

def main(argv):
   aoi = ''
   inworkspace = ''
   ingdb = ''
   try:
      opts, args = getopt.getopt(argv,"hr:w:g:",["region=","workspace="])
   except getopt.GetoptError:
           printHelp()
   for opt, arg in opts:
      if opt in ('-h', '--help'):
         printHelp()
      elif opt in ("-r", "--region"):
         aoi = arg
         if (len(aoi) < 1):
                 print('Region is incorrect')
                 sys.exit(2)
      elif opt in ("-w", "--workspace"):
         inworkspace = arg
         if not (os.path.exists(inworkspace)):
                 print("Workspace folder doesn't exist.  Please create it")
                 sys.exit(2)
      elif opt in ("-g", "--geodatabase"):
         ingdb = arg
         if not (os.path.exists(inworkspace)):
                 print("GDB doesn't exist.  Please create it")
                 sys.exit(2)

   if len(opts) < 3:
        printHelp()
        
   print('Region of interest: ', aoi)
   print('Workspace: ', inworkspace)
   print('GDB: ', ingdb)

if __name__ == "__main__":
   main(sys.argv[1:])