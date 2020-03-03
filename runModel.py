"""
runModel
========
runModel is an example of how to utilize the waterfowlmodel module.
"""

import os, sys, getopt, datetime, logging, arcpy
import waterfowlmodel.base as waterfowl

def printHelp():
         """
         Prints information on how to call this python application from command line
         """
         print('\n\nScript created for utilizing the waterfowl module and running energetic calculations for waterfowl.\n'\
               'Usage: runModel.py -a [Area of interest] -wet [Wetland] -k [kcal Table] -c [Crosswalk table] -w [Workspace]\n\n' \
               'These are the options used to initiate and run the waterfowl model properly.\n\n' \
               'Startup:\n'
               '\t-w, --workspace\t\t Folder path where geodatabase and csv files are stored\n' \
               '\t-g, --geodatabase\t\t Geodatabase that stores features\n' \
               '\t-l, --wetland\t\t Specify the location of thoe wetland layer to use\n' \
               '\t-k, --kcalTable\t Specify location of the wetland type enrgy value CSV file\n' \
               '\t-c, --crosswalk\t\t Specify location of the table that relates different wetlands types to another\n' \
               '\t-d, --demand\t\t Specify location of NAWCA stepdown energy demand layer\n' \
               '\t-a, --aoi\t\t Area of interest layer\n')
         sys.exit(2)

def main(argv):
   """
   Creates a waterfowl model object.
   
   :param workspace: Workspace where geodatabase and csvs are stored.
   :type workspace: str
   :param geodatabase: Geodatabase with features.
   :type geodatabase: str
   :param wetland: National Wetlands Inventory shapefile
   :type wetland: str
   :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by acre]
   :type kcalTable: str
   :param crosswalk: CSV file relating wetland habitat types to kcal csv table
   :type crosswalk: str
   :param demand: NAWCA Stepdown duck energy layer
   :type demand: str
   :param aoi: Area of interest shapefile
   :type aoi: str   
   """
   aoi = ''
   wetland = ''
   kcalTable = ''
   crosswalk = ''
   demand = ''
   workspace = ''
   geodatabase = ''
   scratchgdb = ''
   aoifolder = ''

   try:
      opts, args = getopt.getopt(argv,"hw:g:l:k:c:d:a:",["workspace=","geodatabase", "wetland=", "kcalTable=", "crosswalk=", "demand=", "aoi="])
      if len(opts) < 7:
         printHelp()
   except getopt.GetoptError:
           printHelp()
   for opt, arg in opts:
      if opt in ('-h', '--help'):
         printHelp()
      elif opt in ("-w", "--workspace"):
         workspace = arg
         if not (os.path.exists(workspace)):
                 print("Workspace folder doesn't exist.")
                 sys.exit(2)
      elif opt in ("-g", "--geodatabase"):
         geodatabase = os.path.join(workspace,arg)
         if not (os.path.exists(geodatabase)):
                 print("Geodatabase doesn't exist.")
                 sys.exit(2)                 
      elif opt in ("-l", "--wetland"):
         wetland = os.path.join(geodatabase,arg)
         if not arcpy.Exists(wetland):
                 print("Wetland layer doesn't exist.")
                 sys.exit(2)
      elif opt in ("-k", "--kcalTable"):
         kcalTable = os.path.join(workspace, arg)
         if not (os.path.exists(kcalTable)):
                 print("kcal table doesn't exist.")
                 sys.exit(2)
      elif opt in ("-c", "--crosswalk"):
         crosswalk = os.path.join(workspace,arg)
         if not (os.path.exists(crosswalk)):
                 print("crosswalk table doesn't exist.")
                 sys.exit(2)
      elif opt in ("-d", "--demand"):
         demand = os.path.join(geodatabase,arg)
         if not (arcpy.Exists(demand)):
                 print("energy demand layer doesn't exist.")
                 sys.exit(2)                 
      elif opt in ("-a", "--aoi"):
         aoi = os.path.join(geodatabase,arg)
         if not (os.path.exists(os.path.join(workspace, arg))):
            print('Creating project folder: ', os.path.join(os.path.join(workspace, arg)))
            os.mkdir(os.path.join(workspace, arg))
            scratchgdb = os.path.join(workspace, arg, arg + "_scratch.gdb")
            arcpy.CreateFileGDB_management(os.path.join(workspace,arg), arg+'_scratch.gdb')
            
         else:
            print("Project folder already exists.  Using it")
            scratchgdb = os.path.join(workspace, arg, arg + "_scratch.gdb")
            if not (os.path.exists(scratchgdb)):
               print('Creating scratch geodatabase: ', scratchgdb)
               arcpy.CreateFileGDB_management(os.path.join(workspace,arg), arg+'_scratch.gdb')
            else:
               print("Scratch GDB already exists.  Using it")            
         if not (arcpy.Exists(aoi)):
                 print("aoi layer doesn't exist.")
                 sys.exit(2)
         logging.basicConfig(filename=os.path.join(workspace,"Waterfowl_" + arg + "_" + datetime.datetime.now().strftime("%m_%d_%Y")+ ".log"), filemode='w', level=logging.INFO)                 
   
   print('\nWorkspace: ', workspace)
   print('Wetland layer: ', wetland)
   print('Geodatabase: ', geodatabase)
   print('Kcal Table: ', kcalTable)
   print('Crosswalk table: ', crosswalk)
   print('Energy demand layer: ', demand)
   print('Region of interest: ', aoi)
   print('Scratch gdb: ', scratchgdb)
   print('#####################################\n')

   logging.info("Waterfowl DST run")
   logging.info('Date: ' + datetime.datetime.now().strftime("%m_%d_%Y"))
   logging.info('From Workspace: ' + workspace)
   logging.info('Geodatabase: ' + geodatabase)
   logging.info('Scratch: ' + scratchgdb)
   logging.info('Region of interest: ' + aoi)
   logging.info('Wetland dataset: ' + wetland)
   logging.info('Kcal table: ' + kcalTable)
   logging.info('Crosswalk table: ' + crosswalk)
   logging.info('Energy demand: ' + demand)

   dst = waterfowl.Waterfowlmodel(aoi, wetland, kcalTable, crosswalk, demand, scratchgdb)
   print('Test clip')
   dst.clipStuff()
   print('Prep Energy')
   dst.prepEnergy()
   print('\n Complete')
   print('#####################################\n')

if __name__ == "__main__":
   print('\nRunning model')
   print('#####################################\n')
   main(sys.argv[1:])