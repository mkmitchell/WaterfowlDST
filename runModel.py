"""
runModel
========
runModel is an example of how to utilize the waterfowlmodel module.
"""

import os, sys, getopt, datetime, logging, arcpy, argparse, time
import waterfowlmodel.base as waterfowl
import waterfowlmodel.dataset

def printHelp():
         """
         Prints information on how to call this python application from command line
         """
         print('\n\nScript created for utilizing the waterfowl module and running energetic calculations for waterfowl.\n'\
               'Usage: runModel.py -a [Area of interest] -l [Wetland] -k [kcal Table] -c [Crosswalk table] -w [Workspace]\n\n' \
               'These are the options used to initiate and run the waterfowl model properly.\n\n' \
               'Startup:\n'
               '\t-w, --workspace\t\t Folder path where geodatabase and csv files are stored\n' \
               '\t-g, --geodatabase\t\t Geodatabase that stores features\n' \
               '\t-l, --wetland\t\t Specify the location of thoe wetland layer to use\n' \
               '\t-k, --kcalTable\t Specify location of the wetland type enrgy value CSV file\n' \
               '\t-c, --crosswalk\t\t Specify location of the json file that relates different wetlands types to another\n' \
               '\t-d, --demand\t\t Specify location of NAWCA stepdown energy demand layer\n' \
               '\t-b, --bin\t\t Specify location of aggregation layer\n' \
               '\t-f, --file\t\t Specify a config file full path instead of supplying input via parameters\n'
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
   :param crosswalk: JSON file relating wetland nwi codes to habitat type
   :type crosswalk: str
   :param demand: NAWCA Stepdown duck energy layer
   :type demand: str
   :param aoi: Area of interest shapefile
   :type aoi: str      
   :param bin: Aggregation layer
   :type bin: str   
   :param file: Full config file path
   :type file: str   
   """
   aoi = ''
   wetland = ''
   kcalTable = ''
   crosswalk = ''
   demand = ''
   binIt=''
   workspace = ''
   geodatabase = ''
   scratchgdb = ''
   aoifolder = ''
   extra = {}

   parser=argparse.ArgumentParser(prog=argv)
   parser.add_argument('--workspace', '-w', nargs=1, type=str, default='', help="Workspace where geodatabase and csvs are stored")
   parser.add_argument('--geodatabase', '-g', nargs=1, type=str, default='', help="Geodatabase that stores features")
   parser.add_argument('--wetland', '-l', nargs=2, type=str, default=[], help="Specify the name of the wetland layer and csv file separated by a comma")
   parser.add_argument('--kcalTable', '-k', nargs=1, type=str, default=[], help="Specify the name of the kcal energy table")
   parser.add_argument('--demand', '-d', nargs=1, type=str, default=[], help="Specify name of NAWCA stepdown layer")
   parser.add_argument('--extra', '-e', nargs="*", type=str, default=[], help="Extra habitat datasets in format: full path to dataset 1, full path to crosswalk 1, full path to dataset 2, full path to crosswalk")
   parser.add_argument('--binIt', '-b', nargs=1, type=str, default=[], help="Specify aggregation layer name")
   parser.add_argument('--aoi', '-a', nargs=1, type=str, default=[], help="Specify area of interest layer name")
   
   # parse the command line
   args = parser.parse_args()
   if len(argv) < 8:
      printHelp()
      sys.exit(2)    
   workspace = args.workspace[0]
   if not (os.path.exists(workspace)):
      print("Workspace folder doesn't exist:", workspace)
      sys.exit(2)
   geodatabase = os.path.join(workspace,args.geodatabase[0])
   if not (os.path.exists(geodatabase)):
      print("Geodatabase doesn't exist: ", geodatabase)
      sys.exit(2)             
   wetland = os.path.join(geodatabase,args.wetland[0])
   wetlandX = os.path.join(workspace,args.wetland[1])
   if not arcpy.Exists(wetland):
      print("Wetland layer doesn't exist.", wetland)
      sys.exit(2)
   if not arcpy.Exists(wetlandX):
      print("Wetland crosswalk doesn't exist.")
      sys.exit(2)
   kcalTable = os.path.join(workspace,args.kcalTable[0])
   if not arcpy.Exists(kcalTable):
      print("kcalTable layer doesn't exist.")
      sys.exit(2)
   demand = os.path.join(geodatabase,args.demand[0])
   if not arcpy.Exists(demand):
      print("Demand layer doesn't exist.")
      sys.exit(2)
   if len(args.extra) > 0:
      if len(args.extra)%2 != 0:
         print("Number of extra habitat datasets does not equal crossover tables")
      else:
         extra = {os.path.join(geodatabase,args.extra[i]): os.path.join(workspace,args.extra[i + 1]) for i in range(0, len(args.extra), 2)}
   binIt = os.path.join(geodatabase,args.binIt[0])
   if not arcpy.Exists(binIt):
      print("Aggregation layer doesn't exist.")
      sys.exit(2)
   aoi = os.path.join(geodatabase,args.aoi[0])
   if not (os.path.exists(os.path.join(workspace, args.aoi[0]))):
      print('Creating project folder: ', os.path.join(os.path.join(workspace, args.aoi[0])))
      os.mkdir(os.path.join(workspace, args.aoi[0]))
      scratchgdb = os.path.join(workspace, args.aoi[0], args.aoi[0] + "_scratch.gdb")
      arcpy.CreateFileGDB_management(os.path.join(workspace,args.aoi[0]), args.aoi[0]+'_scratch.gdb')
   else:
      print("Project folder already exists.  Using it")
      scratchgdb = os.path.join(workspace, args.aoi[0], args.aoi[0] + "_scratch.gdb")
      if not (os.path.exists(scratchgdb)):
         print('Creating scratch geodatabase: ', scratchgdb)
         arcpy.CreateFileGDB_management(os.path.join(workspace,args.aoi[0]), args.aoi[0]+'_scratch.gdb')
      else:
         print("Scratch GDB already exists.  Using it")            
   if not (arcpy.Exists(aoi)):
            print("aoi layer doesn't exist.")
            sys.exit(2)
       
   logging.basicConfig(filename=os.path.join(workspace,"Waterfowl_" + args.aoi[0] + "_" + datetime.datetime.now().strftime("%m_%d_%Y")+ ".log"), filemode='w', level=logging.INFO)                 
   wetland = waterfowlmodel.dataset.Dataset(wetland, scratchgdb, wetlandX)
   demand = waterfowlmodel.dataset.Dataset(demand, scratchgdb)
   
   print('\nINPUT')
   print('#####################################')
   print('Workspace: ', workspace)
   print('Wetland layer: ', wetland.inData)
   print('Wetland crosswalk: ', wetland.crosswalk)
   print('Geodatabase: ', geodatabase)
   print('Kcal Table: ', kcalTable)
   print('Energy demand layer: ', demand.inData)
   print('Bin layer: ', binIt)
   print('Extra datasets: ', extra)   
   print('Region of interest: ', aoi)
   print('Scratch gdb: ', scratchgdb)
   print('#####################################\n')

   logging.info("Waterfowl DST run")
   logging.info('Date: ' + datetime.datetime.now().strftime("%m_%d_%Y"))
   logging.info('From Workspace: ' + workspace)
   logging.info('Geodatabase: ' + geodatabase)
   logging.info('Scratch: ' + scratchgdb)
   logging.info('Region of interest: ' + aoi)
   logging.info('Wetland dataset: ' + wetland.inData)
   logging.info('Wetland crosswalk: ' + wetland.crosswalk)
   logging.info('Kcal table: ' + kcalTable)
   logging.info('Energy demand: ' + demand.inData)
   logging.info('Bin layer: ' + binIt)

   startT = time.clock()
   dst = waterfowl.Waterfowlmodel(aoi, wetland.inData, kcalTable, wetland.crosswalk, demand.inData, binIt, scratchgdb)
   print(time.clock() - startT)
   print('\nAfter dst')
   print('#####################################')
   print('Wetland layer: ', dst.wetland)
   print('Energy demand layer: ', dst.demand)
   print('Bin layer: ', dst.binIt)
   print('Region of interest: ', dst.aoi)
   print('Scratch gdb: ', dst.scratch)
   print('#####################################\n')
   startT = time.clock()
   dst.crossClass()
   print(time.clock() - startT)
   print('Prep Energy')
   startT = time.clock()
   dst.prepEnergy()
   print(time.clock() - startT)
   print('Bin Wetland')
   startT = time.clock()
   wetbin = dst.bin(dst.wetland, dst.binIt, 'wetland')
   print(time.clock() - startT)
   print('Bin Demand')
   startT = time.clock()
   demandbin = dst.bin(dst.demand, dst.binIt, 'demand')
   print(time.clock() - startT)
   print('\n Complete')
   print('#####################################\n')

if __name__ == "__main__":
   print('\nRunning model')
   print('#####################################\n')
   main(sys.argv[1:])