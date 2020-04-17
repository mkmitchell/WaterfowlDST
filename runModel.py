"""
runModel
============
runModel is my implementation of utilizing the Waterfowlmodel class to calculate energy demand, supply, and public land acreages within an area of interest.
"""

import os, sys, getopt, datetime, logging, arcpy, argparse, time
import waterfowlmodel.base as waterfowl
import waterfowlmodel.dataset
import waterfowlmodel.publicland

def main(argv):
   """
   Creates a waterfowl model object.
   
   :param workspace: Workspace where geodatabase and csvs are stored.
   :type workspace: str
   :param geodatabase: Geodatabase with features.
   :type geodatabase: str
   :param wetland: National Wetlands Inventory shapefile and csv file separated by a comma
   :type wetland: str
   :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by acre]
   :type kcalTable: str
   :param demand: NAWCA Stepdown duck energy layer
   :type demand: str
   :param extra: Extra habitat datasets in format: full path to dataset 1, full path to crosswalk 1, full path to dataset 2, full path to crosswalk
   :type extra: str
   :param bin: Aggregation layer
   :type bin: str      
   :param aoi: Area of interest shapefile
   :type aoi: str
   """
   aoi = ''
   wetland = ''
   kcalTable = ''
   demand = ''
   binIt=''
   workspace = ''
   geodatabase = ''
   scratchgdb = ''
   aoifolder = ''
   extra = {}
   mergebin = []

   parser=argparse.ArgumentParser(prog=argv)
   parser.add_argument('--workspace', '-w', nargs=1, type=str, default='', help="Workspace where geodatabase and csvs are stored")
   parser.add_argument('--geodatabase', '-g', nargs=1, type=str, default='', help="Geodatabase that stores features")
   parser.add_argument('--wetland', '-l', nargs=2, type=str, default=[], help="Specify the name of the wetland layer and csv file separated by a comma")
   parser.add_argument('--padus', '-p', nargs=1, type=str, default=[], help="Specify the name of the PADUS layer")
   parser.add_argument('--nced', '-n', nargs=1, type=str, default=[], help="Specify the name of the NCED layer")
   parser.add_argument('--kcalTable', '-k', nargs=1, type=str, default=[], help="Specify the name of the kcal energy table")
   parser.add_argument('--demand', '-d', nargs=1, type=str, default=[], help="Specify name of NAWCA stepdown layer")
   parser.add_argument('--extra', '-e', nargs="*", type=str, default=[], help="Extra habitat datasets in format: full path to dataset 1, full path to crosswalk 1, full path to dataset 2, full path to crosswalk")
   parser.add_argument('--binIt', '-b', nargs=1, type=str, default=[], help="Specify aggregation layer name")
   parser.add_argument('--aoi', '-a', nargs=1, type=str, default=[], help="Specify area of interest layer name")
   
   # parse the command line
   args = parser.parse_args()
   print(args)
   if len(argv) < 8:
      parser.print_help()
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
   padus = os.path.join(geodatabase,args.padus[0])
   if not arcpy.Exists(padus):
      print("PADUS layer doesn't exist.", padus)
      sys.exit(2)
   nced = os.path.join(geodatabase,args.nced[0])
   if not arcpy.Exists(nced):
      print("NCED layer doesn't exist.", nced)
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
         print('Extra datasets')
         extra = {i:[os.path.join(geodatabase,args.extra[i]), os.path.join(workspace,args.extra[i + 1])] for i in range(0, len(args.extra), 2)}
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
   padus = waterfowlmodel.dataset.Dataset(padus, scratchgdb)
   nced = waterfowlmodel.dataset.Dataset(nced, scratchgdb)
   
   print('\nINPUT')
   print('#####################################')
   print('Workspace: ', workspace)
   print('Wetland layer: ', wetland.inData)
   print('Wetland crosswalk: ', wetland.crosswalk)
   print('PAD layer: ', padus.inData)
   print('NCED layer: ', nced.inData)
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
   dst = waterfowl.Waterfowlmodel(aoi, wetland.inData, kcalTable, wetland.crosswalk, demand.inData, binIt, extra, scratchgdb)
   print(time.clock() - startT)
   print('\nAfter dst')
   print('#####################################')
   print('Wetland layer: ', dst.wetland)
   print('Wetland crossclass: ', dst.crossTbl)   
   print('Energy demand layer: ', dst.demand)
   print('Bin layer: ', dst.binIt)
   print('Region of interest: ', dst.aoi)
   print('Scratch gdb: ', dst.scratch)
   print('#####################################\n')
   startT = time.clock()
   print('Wetland crossclass')
   #dst.crossClass(dst.wetland, dst.crossTbl, 'ATTRIBUTE')
   print('Marsh crossclass')
   #dst.crossClass(dst.extra[0][0], dst.extra[0][1], 'frmCLS')
   print('Join features')
   allEnergy = dst.joinFeatures()
   print('Prep Energy')
   #dst.prepEnergy()
   print('Bin Wetland')
   #wetbin = dst.bin(allEnergy, dst.binIt, 'EnergySupply')
   wetbin = waterfowlmodel.base.Waterfowlmodel.aggproportion(dst.binIt, allEnergy, "OBJECTID", ["avalNrgy"], ["HUC12"], dst.scratch, "supplyenergy")
   arcpy.AlterField_management(wetbin, 'SUM_avalNrgy', 'avalNrgy', 'avalNrgy')
   mergebin.append(wetbin)
   print(time.clock() - startT)
   print('Bin Demand')
   #demandbin = dst.bin(dst.demand, dst.binIt, 'demand')
   demandbin = waterfowlmodel.base.Waterfowlmodel.aggproportion(dst.binIt, dst.demand, "OBJECTID", ["LTADUD"], ["HUC12"], dst.scratch, "energydemand")
   arcpy.AlterField_management(demandbin, 'SUM_LTADUD', 'LTADUD', 'LTADUD')
   mergebin.append(demandbin)
   print("Combine supply demand")
   #dst.unionEnergy(wetbin, demandbin)
   print('Public land')
   nced = waterfowlmodel.publicland.PublicLand(dst.aoi, nced.inData, 'nced', dst.binIt, dst.scratch)
   padus = waterfowlmodel.publicland.PublicLand(dst.aoi, padus.inData, 'padus', dst.binIt, dst.scratch)
   print('bin nced')
   ncedbin = waterfowlmodel.base.Waterfowlmodel.aggproportion(nced.binIt, nced.land, "OBJECTID", ["gis_acres"], ["HUC12"], dst.scratch, "nced")
   arcpy.AlterField_management(ncedbin, 'SUM_gis_acres', 'NCEDAcre', 'NCEDAcre')
   mergebin.append(ncedbin)
   print('bin padus')
   padusbin = waterfowlmodel.base.Waterfowlmodel.aggproportion(padus.binIt, padus.land, "OBJECTID", ["gis_acres"], ["HUC12"], dst.scratch, "pad")
   arcpy.AlterField_management(padusbin, 'SUM_gis_acres', 'PADAcre', 'PADAcre')
   mergebin.append(padusbin)
   print('Merge it all')
   arcpy.Merge_management(mergebin, os.path.join(scratchgdb, 'AllDataBin'))
   print('\n Complete')
   print('#####################################\n')

if __name__ == "__main__":
   print('\nRunning model')
   print('#####################################\n')
   main(sys.argv[1:])