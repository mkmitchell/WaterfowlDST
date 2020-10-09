"""
runModel
============
runModel is my implementation of utilizing the Waterfowlmodel class to calculate energy demand, supply, and public land area within an area of interest.
"""

import os, sys, getopt, datetime, logging, arcpy, argparse, time
import waterfowlmodel.base as waterfowl
import waterfowlmodel.dataset
import waterfowlmodel.publicland

def printlog(txt, var):
   print(txt + ':', var)
   logging.info(txt + ': ' + var)

def main(argv):
   """
   Creates a waterfowl model object.
   
   :param workspace: Workspace where geodatabase and csvs are stored.
   :type workspace: str
   :param geodatabase: Geodatabase with features.
   :type geodatabase: str
   :param wetland: National Wetlands Inventory shapefile and csv file separated by a comma
   :type wetland: str
   :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by ha]
   :type kcalTable: str
   :param demand: NAWCA Stepdown duck energy layer
   :type demand: str
   :param extra: Extra habitat datasets in format: full path to dataset 1, full path to crosswalk 1, full path to dataset 2, full path to crosswalk
   :type extra: str
   :param bin: Aggregation layer
   :type bin: str      
   :param aoi: Area of interest shapefile
   :type aoi: str
   :param binUnique: Area of interest unique column identifier
   :type binUnique: str   
   """
   aoi = ''
   aoiname = ''
   binUnique = ''
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
   parser.add_argument('--binUnique', '-u', nargs=1, type=str, default=[], help="Specify the aggregation layer unique column")
   parser.add_argument('--aoi', '-a', nargs=1, type=str, default=[], help="Specify area of interest layer name")
   parser.add_argument('--debug', '-z', nargs=5, type=int,default=[], help="Run algorithm.  True or False.  Energy supply, Energy demand, protected lands, habitat proportion")
   
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
   binUnique = args.binUnique[0]    
   if not len(arcpy.ListFields(binIt,binUnique))>0:
      print("AOI field doesn't have the unique identifier.")
      sys.exit(2)
   aoi = os.path.join(geodatabase,args.aoi[0])
   aoiname = args.aoi[0]
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
   if args.debug:
      debug = args.debug
   else:
      debug = [0, 0, 0, 0, 0]
       
   logging.basicConfig(filename=os.path.join(workspace,"Waterfowl_" + aoiname + "_" + datetime.datetime.now().strftime("%m_%d_%Y")+ ".log"), filemode='w', level=logging.INFO)                 
   wetland = waterfowlmodel.dataset.Dataset(wetland, scratchgdb, wetlandX)
   demand = waterfowlmodel.dataset.Dataset(demand, scratchgdb)
   padus = waterfowlmodel.dataset.Dataset(padus, scratchgdb)
   nced = waterfowlmodel.dataset.Dataset(nced, scratchgdb)
   
   print('\nModel Input parameters')
   print('#####################################')
   printlog('Workspace', workspace)
   printlog('Date', datetime.datetime.now().strftime("%m_%d_%Y"))
   printlog('Wetland layer', wetland.inData)
   printlog('Wetland crosswalk', wetland.crosswalk)
   printlog('PAD', padus.inData)
   printlog('NCED', nced.inData)
   printlog('Geodatabase', geodatabase)
   printlog('Energy Supply table', kcalTable)
   printlog('Energy demand layer', demand.inData)
   printlog('Bin layer', binIt)
   printlog('Bin unique', binUnique)
   printlog('Extra datasets', ' '.join(map(str, list(extra))))
   printlog('Bin layer', binIt)
   printlog('Region of interest', aoi)
   printlog('Scratch gdb', scratchgdb)
   printlog('Debugging', ' '.join(map(str, list(debug))))
   print('#####################################\n')

   startT = time.clock()
   dst = waterfowl.Waterfowlmodel(aoi, aoiname, wetland.inData, kcalTable, wetland.crosswalk, demand.inData, binIt, binUnique, extra, scratchgdb, debug)
   print(time.clock() - startT)
   print('\nWaterfowl object data')
   print('#####################################')
   printlog('Wetland layer', ' '.join(map(str, list(dst.__dict__))))
   #print('Wetland layer: ', dst.wetland)
   #print('Wetland crossclass: ', dst.crossTbl)   
   #print('Energy demand layer: ', dst.demand)
   #print('Bin layer: ', dst.binIt)
   #print('Region of interest: ', dst.aoi)
   #print('Scratch gdb: ', dst.scratch)
   print('#####################################\n')
   startT = time.clock()
   if debug[0]: #Energy supply
      print('#### ENERGY SUPPLY ####')
      print('Wetland crossclass')
      dst.crossClass(dst.wetland, dst.crossTbl, 'ATTRIBUTE')
      print('Marsh crossclass')
      dst.crossClass(dst.extra[0][0], dst.extra[0][1], 'frmCLS')
      print('Impoundments crossclass')
      dst.crossClass(dst.extra[1][0], dst.extra[1][1])
      print('Join habitats')
      allEnergy = dst.joinEnergy(dst.mergedenergy, dst.wetland, dst.extra)
      print('Prep Energy')
      allEnergy = dst.prepEnergyFast(allEnergy, dst.kcalTbl)
      allEnergy = dst.mergedenergy
      print('Merge Energy')
      dst.mergedenergy = arcpy.SelectLayerByAttribute_management(in_layer_or_view=allEnergy, selection_type="NEW_SELECTION", where_clause="CLASS IS NOT NULL")
      wetbin = waterfowlmodel.base.Waterfowlmodel.aggproportion(dst.binIt, allEnergy, "OBJECTID", ["avalNrgy", "CalcHA"], ["HUC12"], dst.scratch, "supplyenergy")
      if not len(arcpy.ListFields(wetbin,'THabNrg'))>0:
         arcpy.AlterField_management(wetbin, 'SUM_avalNrgy', 'THabNrg', 'TotalHabitatEnergy')
      if not len(arcpy.ListFields(wetbin,'THabHA'))>0:
         arcpy.AlterField_management(wetbin, 'SUM_CalcHA', 'THabHA', 'TotalHabitatHA')
   else:
      wetbin = os.path.join(dst.scratch, 'aggtosupplyenergy')

   if debug[1]: #Energy demand
      print('#### ENERGY DEMAND ####')
      dst.demand = arcpy.SelectLayerByAttribute_management(in_layer_or_view=dst.demand, selection_type="NEW_SELECTION", where_clause="species = 'All' AND CODE = '4B'")
      demandbin = waterfowlmodel.base.Waterfowlmodel.aggproportion(dst.binIt, dst.demand, "OBJECTID", ["LTADUD", "LTADemand"], ["HUC12"], dst.scratch, "energydemand")
      if not len(arcpy.ListFields(demandbin,'TLTADUD'))>0:
         arcpy.AlterField_management(demandbin, 'SUM_LTADUD', 'TLTADUD', 'TotalLTADUD')
      if not len(arcpy.ListFields(demandbin,'TLTADmnd'))>0:
         arcpy.AlterField_management(demandbin, 'SUM_LTADemand', 'TLTADmnd', 'TotalLTADemand')
   else:
      demandbin = os.path.join(dst.scratch, 'aggtoenergydemand')

   if debug[2]: #Public lands
      print('#### PUBLIC LANDS ####')
      nced = waterfowlmodel.publicland.PublicLand(dst.aoi, nced.inData, 'nced', dst.binIt, dst.scratch)
      padus = waterfowlmodel.publicland.PublicLand(dst.aoi, padus.inData, 'padus', dst.binIt, dst.scratch)
      print('Public lands ready.  Analyzing')
      dst.prepProtected(nced.land, padus.land)
      protectedbin = waterfowlmodel.base.Waterfowlmodel.aggproportion(dst.binIt, dst.protectedMerge, "OBJECTID", ["CalcHA"], ["HUC12"], dst.scratch, "protectedbin")
      if not len(arcpy.ListFields(protectedbin,'ProtHA'))>0:
         if len(arcpy.ListFields(dst.protectedbin,'SUM_CalcHA'))>0:
            arcpy.AlterField_management(protectedbin, 'SUM_CalcHA', 'ProtHA', 'ProtectedHectares')
         else:
            arcpy.AlterField_management(protectedbin, 'CalcHA', 'ProtHA', 'ProtectedHectares')
      print('Calculate and bin protected habitat energy and hectares')
      dst.calcProtected()
      dst.protectedEnergy = waterfowlmodel.base.Waterfowlmodel.aggproportion(dst.binIt, dst.protectedEnergy, "OBJECTID", ["CalcHA", "avalNrgy"], ["HUC12"], dst.scratch, "protectedEnergy")
      if not len(arcpy.ListFields(dst.protectedEnergy,'ProtHabHA'))>0:
         if len(arcpy.ListFields(dst.protectedEnergy,'SUM_CalcHA'))>0:
            arcpy.AlterField_management(dst.protectedEnergy, 'SUM_CalcHA', 'ProtHabHA', 'ProtectedHabitatHectares')
         else:
            arcpy.AlterField_management(dst.protectedEnergy, 'CalcHA', 'ProtHabHA', 'ProtectedHabitatHectares')
      if not len(arcpy.ListFields(dst.protectedEnergy,'ProtHabNrg'))>0:
         if len(arcpy.ListFields(dst.protectedEnergy,'SUM_avalNrgy'))>0:   
            arcpy.AlterField_management(dst.protectedEnergy, 'SUM_avalNrgy', 'ProtHabNrg', 'ProtectedHabitatEnergy')
         else:
            arcpy.AlterField_management(dst.protectedEnergy, 'avalNrgy', 'ProtHabNrg', 'ProtectedHabitatEnergy')
   else:
      dst.protectedEnergy = (os.path.join(dst.scratch, 'aggtoprotectedEnergy'))
   
   if debug[3]: #Habitat percentage
      print('#### HABITAT PERCENTAGE ####')
      dst.prepnpTables()
      habpct = dst.pctHabitatType()
   else:
      habpct = os.path.join(dst.scratch,'HabitatInAOI')
   
   if debug[4]: #Habitat weighted mean
      print('#### HABITAT WEIGHTED MEAN ####')
      #if not debug[3]:
         #dst.prepnpTables()
      habpct = dst.weightedMean()
   else:
      habpct = os.path.join(dst.scratch,'HabitatInAOI')

   print('\n#### Merging all the data for output ####')
   mergebin.append(dst.unionEnergy(wetbin, demandbin)) #Energy supply and demand
   mergebin.append(os.path.join(dst.scratch, 'aggtoprotectedbin')) #Protected acres
   mergebin.append(dst.protectedEnergy) #Protected energy
   mergebin.append(habpct) #Habitat proportions
   print(mergebin)
   dst.dstOutout(mergebin, ['HUC12'])
   print(time.clock() - startT)
   print('\n Complete')
   print('#####################################\n')

if __name__ == "__main__":
   print('\nRunning model')
   print('#####################################\n')
   main(sys.argv[1:])