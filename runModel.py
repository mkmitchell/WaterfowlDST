"""
runModel
========
runModel is an example of how to utilize the waterfowlmodel module.
"""

import os, sys, getopt, datetime, logging

def printHelp():
         """
         Prints information on how to call this python application from command line
         """
         print('\n\nScript created for utilizing the waterfowl module and running energetic calculations for waterfowl.\n'\
               'Usage: runModel.py -a [Area of interest] -wet [Wetland] -k [kcal Table] -c [Crosswalk table] -w [Workspace]\n\n' \
               'These are the options used to initiate and run the waterfowl model properly.\n\n' \
               'Startup:\n'
               '\t-a, --aoi\t\t Area of interest layer\n' \
               '\t-wet, --wetland\t\t Specify the location of thoe wetland layer to use\n' \
               '\t-kcal, --kcalTable\t Specify location of the wetland type enrgy value CSV file\n' \
               '\t-c, --crosswalk\t\t Specify location of the table that relates different wetlands types to another\n' \
               '\t-d, --demand\t\t Specify location of NAWCA stepdown energy demand layer\n' \
               '\t-w, --workspace\t\t Folder path that all files are located\n')
         sys.exit(2)

def main(argv):
   """
   Creates a waterfowl model object.
    
   :param aoi: Area of interest shapefile
   :type aoi: str
   :param wetland: National Wetlands Inventory shapefile
   :type wetland: str
   :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by acre]
   :type kcalTable: str
   :param crosswalk: CSV file relating wetland habitat types to kcal csv table
   :type crosswalk: str
   :param demand: NAWCA Stepdown duck energy layer
   :type demand: str
   :param workspace: Workspace where temporary features and output will be stored
   :type workspace: str
   """
   aoi = ''
   wetland = ''
   kcalTable = ''
   crosswalk = ''
   demand = ''
   workspace = ''

   try:
      opts, args = getopt.getopt(argv,"hw:l:k:c:d:a:",["workspace=","wetland=", "kcalTable=", "crosswalk=", "demand=", "aoi="])
      if len(opts) < 6:
         printHelp()
   except getopt.GetoptError:
           printHelp()
   for opt, arg in opts:
      if opt in ('-h', '--help'):
         printHelp()
      elif opt in ("-w", "--workspace"):
         workspace = arg
         if not (os.path.exists(workspace)):
                 print("Workspace folder doesn't exist.  Please create it")
                 sys.exit(2)   
      elif opt in ("-l", "--wetland"):
         wetland = arg
         if not (os.path.exists(os.path.join(workspace,wetland))):
                 print("Wetland layer doesn't exist.")
                 sys.exit(2)
      elif opt in ("-k", "--kcalTable"):
         kcalTable = arg
         if not (os.path.exists(os.path.join(workspace, kcalTable))):
                 print("kcal table doesn't exist.")
                 sys.exit(2)
      elif opt in ("-c", "--crosswalk"):
         crosswalk = arg
         if not (os.path.exists(os.path.join(workspace,crosswalk))):
                 print("crosswalk table doesn't exist.")
                 sys.exit(2)
      elif opt in ("-d", "--demand"):
         demand = arg
         if not (os.path.exists(os.path.join(workspace,crosswalk))):
                 print("energy demand layer doesn't exist.")
                 sys.exit(2)                 
      elif opt in ("-a", "--aoi"):
         aoi = arg
         if not (os.path.exists(os.path.join(workspace,aoi))):
                 print("aoi layer doesn't exist.")
                 sys.exit(2)                 
   
   print('\nWorkspace: ', workspace)
   print('Wetland layer: ', wetland)
   print('Kcal Table: ', kcalTable)
   print('Crosswalk table: ', crosswalk)
   print('Energy demand layer: ', demand)
   print('Region of interest: ', aoi)
   
   logging.basicConfig(filename=os.path.join(workspace,"Waterfowl_" + aoi + "_" + datetime.datetime.now().strftime("%m_%d_%Y")+ ".log"), filemode='w', level=logging.INFO)
   logging.info("Waterfowl DST run")
   logging.info('Date: ' + datetime.datetime.now().strftime("%m_%d_%Y"))
   logging.info('Region of interest: ' + aoi)
   logging.info('From Workspace: ' + workspace)
   logging.info('Wetland dataset: ' + wetland)
   logging.info('Kcal table: ' + kcalTable)
   logging.info('Crosswalk table: ' + crosswalk)
   logging.info('Energy demand: ' + demand)

if __name__ == "__main__":
   main(sys.argv[1:])