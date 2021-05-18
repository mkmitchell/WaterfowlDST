"""
runModel
============
Implementation of the Waterfowlmodel class to calculate energy demand, supply, and public land area within an area of interest.
"""

import os, sys, getopt, datetime, logging, arcpy, argparse, time
from functools import wraps
import waterfowlmodel.base as waterfowl
import waterfowlmodel.dataset
import waterfowlmodel.publicland
import waterfowlmodel.zipup
import numpy as np

def printlog(txt, var):
   print(txt + ':', var)
   logging.info(txt + ': ' + var)

def report_time(func):
    '''Decorator reporting the execution time'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(func.__name__, round(end-start,3))
        return result
    return wrapper

@report_time
def main(argv):
   """
   Creates a waterfowl model object.
   
   :param workspace: Workspace where geodatabase and csvs are stored.
   :type workspace: str
   :param geodatabase: Geodatabase with features.
   :type geodatabase: str
   :param wetland: National Wetlands Inventory shapefile and csv file separated by a comma
   :type wetland: str
   :param padus: Protected Area Dataset - US
   :type padus: str
   :param nced: National Conservation Easement Database
   :type nced: str      
   :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by ha]
   :type kcalTable: str
   :param demand: NAWCA Stepdown duck energy layer
   :type demand: str
   :param extra: Extra habitat datasets in format: full path to dataset 1, full path to crosswalk 1, full path to dataset 2, full path to crosswalk
   :type extra: str
   :param binIt: Aggregation layer
   :type binIt: str      
   :param binUnique: Area of interest unique column identifier
   :type binUnique: str   
   :param aoi: Area of interest shapefile
   :type aoi: str
   :param debug: Run sections of code for debugging.  1 = run code and 0 = don't run code section.  Defaults to run everything if not specified. [Supply, demand, species proportion, protected lands, habitat proportion, urban, data check, zip it]
   :type debug: str 
   :param fieldTable: Table to standardize field names and aliases, this csv: ModelOutputFieldDictionary.csv
   :type fieldTable: str
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
   outputgdb = ''
   outputFolder = ''
   fieldTable = ''
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
   parser.add_argument('--binUnique', '-u', nargs=2, type=str, default=[], help="Specify the aggregation layer unique column and name")
   parser.add_argument('--urban', '-r', nargs=1, type=str, default=[], help="Specify urban layer name")
   parser.add_argument('--aoi', '-a', nargs=1, type=str, default=[], help="Specify are a of interest layer name")
   parser.add_argument('--fieldTable', '-f', nargs="*", type=str, default=[], help='Specify crosswalk to standardize field names and aliases.')
   parser.add_argument('--debug', '-z', nargs=8, type=int,default=[], help="Run specific sections of code.  1 or 0 for [Energy supply, Energy demand, Species proportion, protected lands, habitat proportion, urban, data check, zip]")
   
   # parse the command line
   args = parser.parse_args()
   print('')
   #print(args)
   if len(argv) < 12:
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
         extra = {i:[os.path.join(geodatabase,args.extra[i]), os.path.join(workspace,args.extra[i + 1])] for i in range(0, len(args.extra), 2)}
   if len(args.fieldTable) > 0:
      fieldTable = os.path.join(workspace, args.fieldTable[0])
      if not os.path.isfile(fieldTable):
         print("Field table doesn't exist.")
         sys.exit(2)         
   else:
      fieldTable = ''
   binIt = os.path.join(geodatabase,args.binIt[0])
   if not arcpy.Exists(binIt):
      print("Aggregation layer doesn't exist.")
      sys.exit(2)
   binUnique = args.binUnique  
   if not len(arcpy.ListFields(binIt,binUnique))>0:
      print("AOI field doesn't have the unique identifier.")
      sys.exit(2)
   urban = os.path.join(geodatabase,args.urban[0])
   if not arcpy.Exists(urban):
      print("Urban layer doesn't exist.")
      sys.exit(2)      
   aoi = os.path.join(geodatabase,args.aoi[0])
   aoiname = args.aoi[0]
   aoiworkspace = os.path.join(os.path.join(workspace, args.aoi[0]))
   outputFolder = os.path.join(workspace, args.aoi[0], 'output')
   if not (os.path.exists(os.path.join(workspace, args.aoi[0]))):
      print('Creating project folder: ', os.path.join(os.path.join(workspace, args.aoi[0])))
      os.mkdir(os.path.join(workspace, args.aoi[0]))
      os.mkdir(outputFolder)
      scratchgdb = os.path.join(workspace, args.aoi[0], args.aoi[0] + "_scratch.gdb")
      outputgdb = os.path.join(workspace, args.aoi[0], 'output', args.aoi[0] + "_output.gdb")
      arcpy.CreateFileGDB_management(os.path.join(workspace,args.aoi[0]), args.aoi[0]+'_scratch.gdb')
      arcpy.CreateFileGDB_management(outputFolder, args.aoi[0]+'_output.gdb')
   else:
      #print("Project folder already exists.  Using it")
      scratchgdb = os.path.join(workspace, args.aoi[0], args.aoi[0] + "_scratch.gdb")
      outputgdb = os.path.join(workspace, args.aoi[0], 'output', args.aoi[0] + "_output.gdb")
      if not (os.path.exists(scratchgdb)):
         print('Creating scratch geodatabase: ', scratchgdb)
         arcpy.CreateFileGDB_management(scratchgdb)
      if not os.path.exists(outputFolder):
         os.mkdir(outputFolder)
      if not (os.path.exists(outputgdb)):
         print('Creating output geodatabase: ', outputgdb)
         arcpy.CreateFileGDB_management(outputFolder, args.aoi[0]+'_output.gdb')          
   if not (arcpy.Exists(aoi)):
            print("aoi layer doesn't exist.")
            sys.exit(2)
   if args.debug:
      debug = args.debug
   else:
      debug = [1, 1, 1, 1, 1, 1, 1, 1]
   if debug[2] == 1 and fieldTable == '':
      print('Field table not defined but option is enabled')
      sys.exit(2)
       
   logging.basicConfig(filename=os.path.join(workspace,"Waterfowl_" + aoiname + "_" + datetime.datetime.now().strftime("%m_%d_%Y")+ ".log"), filemode='w', level=logging.INFO)                 
   wetland = waterfowlmodel.dataset.Dataset(wetland, scratchgdb, wetlandX)
   demand = waterfowlmodel.dataset.Dataset(demand, scratchgdb)
   urban = waterfowlmodel.dataset.Dataset(urban, scratchgdb)
   padus = waterfowlmodel.dataset.Dataset(padus, scratchgdb)
   nced = waterfowlmodel.dataset.Dataset(nced, scratchgdb)
   
   print('\nModel Input parameters')
   print('#####################################')
   printlog('\tWorkspace', workspace)
   printlog('\tAOI Workspace', aoiworkspace)
   printlog('\tDate', datetime.datetime.now().strftime("%m_%d_%Y"))
   printlog('\tWetland layer', wetland.inData)
   printlog('\tWetland crosswalk', wetland.crosswalk)
   printlog('\tPAD', padus.inData)
   printlog('\tNCED', nced.inData)
   printlog('\tGeodatabase', geodatabase)
   printlog('\tEnergy Supply table', kcalTable)
   printlog('\tEnergy demand layer', demand.inData)
   printlog('\tStandardized Field Names', fieldTable)
   printlog('\tUrban layer', urban.inData)
   printlog('\tBin layer', binIt)
   printlog('\tBin unique', ', '.join(binUnique))
   printlog('\tExtra datasets', str(int(len(args.extra)/2)))
   printlog('\tBin layer', binIt)
   printlog('\tRegion of interest', aoi)
   printlog('\tScratch gdb', scratchgdb)
   printlog('\tOutput gdb', outputgdb)
   printlog('\tDebugging', ' '.join(map(str, list(debug))))
   print('#####################################')

   startT = time.perf_counter()
   print('\n#### Create waterfowl object ####')
   dst = waterfowl.Waterfowlmodel(aoi, aoiname, wetland.inData, kcalTable, wetland.crosswalk, demand.inData, urban.inData, binIt, binUnique, extra, fieldTable, scratchgdb)
   logging.info('Wetland layer '.join(map(str, list(dst.__dict__))))
   if debug[0]: #Energy supply
      print('\n#### ENERGY SUPPLY ####')
      print('\tWetland crossclass')
      dst.wetland = dst.supaCrossClass(dst.wetland, dst.crossTbl)
      #print(dst.extra.keys())
      for i in dst.extra.keys():
         dst.crossClass(dst.extra[i][0], dst.extra[i][1])
      print('\tJoin supply habitats')
      if int(len(args.extra)/2) > 0:
         dst.mergedenergy = dst.joinEnergy(dst.wetland, dst.extra, dst.mergedenergy)
      else:
         dst.mergedenergy = dst.wetland
      print('\tPrep supply Energy')
      dst.mergedenergy = dst.prepEnergyFast(dst.mergedenergy, dst.kcalTbl)
      print('\tMerge supply Energy')
      allEnergy = arcpy.SelectLayerByAttribute_management(in_layer_or_view=dst.mergedenergy, selection_type="NEW_SELECTION", where_clause="CLASS IS NOT NULL")
      arcpy.CopyFeatures_management(allEnergy, dst.mergedenergy + 'Selection')
      dst.mergedenergy = dst.mergedenergy + 'Selection'
      #pdClean = dst.pandasClean(aoiworkspace, dst.mergedenergy)
      dst.mergedenergy = dst.cleanMe(dst.mergedenergy)
      dst.energysupply = dst.aggproportion(dst.binIt, dst.mergedenergy, "OBJECTID", ["avalNrgy", "CalcHA"], [dst.binUnique], dst.scratch, "supplyenergy")
      if not len(arcpy.ListFields(dst.energysupply,'THabNrg'))>0:
         arcpy.AlterField_management(dst.energysupply, 'SUM_avalNrgy', 'THabNrg', 'TotalHabitatEnergy')
      if not len(arcpy.ListFields(dst.energysupply,'THabHA'))>0:
         arcpy.AlterField_management(dst.energysupply, 'SUM_CalcHA', 'THabHA', 'TotalHabitatHA')
   else:
      dst.energysupply = os.path.join(dst.scratch, 'aggtosupplyenergy')
      if not int(len(args.extra)/2) > 0:
         dst.mergedenergy = dst.wetland

   if debug[1]: #Energy demand
      print('\n#### ENERGY DEMAND ####')
      selectDemand = arcpy.SelectLayerByAttribute_management(in_layer_or_view=dst.demand, selection_type="NEW_SELECTION", where_clause="species = 'All'")
      if arcpy.management.GetCount(selectDemand)[0] > "0":
         #arcpy.CopyFeatures_management(selectDemand, os.path.join(dst.scratch, 'EnergyDemandSelected'))
         demandSelected = os.path.join(dst.scratch, 'EnergyDemandSelected')
         mergedAll, wtmarray = dst.prepnpTables(demandSelected, dst.binIt, dst.mergedenergy, dst.scratch)
         dst.demand = dst.aggByField(mergedAll, dst.scratch, demandSelected, dst.binIt, 'energydemand')
      elif arcpy.management.GetCount(selectDemand)[0] == "0":
         print('No records with "All" species. Not calculated')
   else:
      demandSelected = os.path.join(dst.scratch, 'EnergyDemandSelected')
      dst.demand = os.path.join(dst.scratch, 'aggByFieldenergydemanddissolveHUC')
      dst.origDemand = demand.inData

   if debug[2]: #Species proportion
      print('\n#### ENERGY DEMAND BY SPECIES ####')
      demandSp = dst.summarizebySpecies(dst.origDemand, dst.scratch, dst.binIt, os.path.join(dst.scratch, 'MergeAll'), fieldTable)

   if debug[3]: #Public lands
      print('\n#### PUBLIC LANDS ####')
      nced = waterfowlmodel.publicland.PublicLand(dst.aoi, nced.inData, 'nced', dst.binIt, dst.scratch)
      padus = waterfowlmodel.publicland.PublicLand(dst.aoi, padus.inData, 'padus', dst.binIt, dst.scratch)
      print('\tPublic lands ready. Analyzing')
      #dst.prepProtected([nced.land, padus.land])
      dst.protectedMerge = dst.pandasMerge(padus.land, nced.land, os.path.join(aoiworkspace, "Protected" + aoiname + ".shp"))
      protectedbin = dst.aggproportion(dst.binIt, dst.protectedMerge, "OBJECTID", ["CalcHA"], [dst.binUnique], dst.scratch, "protectedbin")
      if not len(arcpy.ListFields(protectedbin,'ProtHA'))>0:
         if len(arcpy.ListFields(protectedbin,'SUM_CalcHA'))>0:
            arcpy.AlterField_management(protectedbin, 'SUM_CalcHA', 'ProtHA', 'ProtectedHectares')
         else:
            arcpy.AlterField_management(protectedbin, 'CalcHA', 'ProtHA', 'ProtectedHectares')
      print('\tCalculate and bin protected habitat energy and hectares')
      dst.calcProtected(dst.mergedenergy, dst.protectedMerge, dst.protectedEnergy)
      dst.protectedEnergy = dst.aggproportion(dst.binIt, dst.protectedEnergy, "OBJECTID", ["CalcHA", "avalNrgy"], [dst.binUnique], dst.scratch, "protectedEnergy")
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
      dst.protectedEnergy = os.path.join(dst.scratch, 'aggtoprotectedEnergy')
      dst.protectedMerge = os.path.join(aoiworkspace, "Protected" + aoiname + ".shp")
   
   if debug[4]: #Habitat proportions
      print('\n#### HABITAT PERCENTAGE ####')
      if not debug[1]:
         mergedAll, wtmarray = dst.prepnpTables(dst.demand, dst.binIt, dst.mergedenergy, dst.scratch)
      habpct = dst.pctHabitatType(dst.binUnique[0], wtmarray)

   print('\n#### HABITAT WEIGHTED MEAN ####')
   if not debug[1]:
      mergedAll, wtmarray = dst.prepnpTables(dst.demand, dst.binIt, dst.mergedenergy, dst.scratch)
   dst.weightedMean(dst.demand, wtmarray)

   if debug[5]:
      print('\n#### Calculate Urban HA ####')
      if not len(arcpy.ListFields(dst.urban,'CalcHA'))>0:
         arcpy.AddField_management(dst.urban, 'CalcHA', "DOUBLE", 9, 2, "", "Hectares")
      arcpy.CalculateGeometryAttributes_management(dst.urban, "CalcHA AREA", area_unit="HECTARES")
      dst.urban = dst.aggproportion(dst.binIt, dst.urban, "OBJECTID", ["CalcHA"], [dst.binUnique], dst.scratch, "urban")
      if len(arcpy.ListFields(dst.urban,'SUM_CalcHA'))>0:
         arcpy.AlterField_management(dst.urban, 'SUM_CalcHA', 'UrbanHA', 'Urban Hectares')
   else:
      dst.urban = os.path.join(dst.scratch, 'aggtourban')

   print('\n#### Merging all the data for output ####')
   print(dst.energysupply)
   print(dst.demand)
   mergebin.append(dst.unionEnergy(dst.energysupply, dst.demand)) #Energy supply and demand
   mergebin.append(os.path.join(dst.scratch, 'aggtoprotectedbin')) #Protected acres
   mergebin.append(dst.protectedEnergy) #Protected energy
   mergebin.append(dst.urban) #Urban - available HA
   outData = dst.dstOutput(mergebin, [dst.binUnique], outputgdb)

   if debug[6]: #Data check
      np.set_printoptions(suppress=True)
      print('\n#### Checking data ####')
      arcpy.Statistics_analysis(in_table=outData, out_table=os.path.join(dst.scratch, 'outputStats'), statistics_fields="THabNrg SUM; TLTADemand SUM; TLTADUD SUM; ProtHA SUM")
      arcpy.Statistics_analysis(in_table=dst.mergedenergy, out_table=os.path.join(dst.scratch, 'mergedEnergyStats'), statistics_fields="avalNrgy SUM")
      arcpy.Statistics_analysis(in_table=demandSelected, out_table=os.path.join(dst.scratch, 'demandStats'), statistics_fields="LTADemand SUM; LTADUD SUM")
      arcpy.Statistics_analysis(in_table=dst.protectedMerge, out_table=os.path.join(dst.scratch, 'protStats'), statistics_fields="CalcHA SUM")
      outputStats = arcpy.da.TableToNumPyArray(os.path.join(dst.scratch, 'outputStats'), ['SUM_THabNrg', 'SUM_TLTADemand', 'SUM_TLTADUD','SUM_ProtHA'])
      inenergystats = arcpy.da.TableToNumPyArray(os.path.join(dst.scratch, 'mergedEnergyStats'), ['SUM_avalNrgy'])
      indemandstats = arcpy.da.TableToNumPyArray(os.path.join(dst.scratch, 'demandStats'), ['SUM_LTADemand', 'SUM_LTADUD'])
      inprotstats = arcpy.da.TableToNumPyArray(os.path.join(dst.scratch, 'protStats'), ['SUM_CalcHA'])
      print('\nOutput energy: {}\nInput energy: {}'.format(outputStats[0][0], inenergystats[0][0]))
      print('\tEnergy difference %: {}'.format(int((outputStats[0][0] - inenergystats[0][0])/(outputStats[0][0] + inenergystats[0][0])*100)))
      print('\nOutput demand: {}\nInput demand: {}'.format(outputStats[0][1], indemandstats[0][0]))
      print('\tDemand  difference %: {}'.format(int((outputStats[0][1] - indemandstats[0][0])/(outputStats[0][1] + indemandstats[0][0])*100)))
      print('\nOutput DUD: {}\nInput DUD: {}'.format(outputStats[0][2], indemandstats[0][1]))
      print('\tDUD  difference %: {}'.format(int((outputStats[0][2] - indemandstats[0][1])/(outputStats[0][2] + indemandstats[0][1])*100)))
      print('\nOutput Protection HA: {}\nInput HA: {}'.format(outputStats[0][3], inprotstats[0][0]))
      print('\tProtection  difference %: {}'.format(int((outputStats[0][3] - inprotstats[0][0])/(outputStats[0][3] + inprotstats[0][0])*100)))

   if debug[7]: #Zip it
      print('\n#### Zip data ####')
      #print('\tAdd HUC')
      #waterfowlmodel.zipup.AddHUCNames(outData, binIt,'HUC12', 'huc12')
      arcpy.ClearWorkspaceCache_management()
      try:
         waterfowlmodel.zipup.zipUp(os.path.join(os.path.join(workspace, args.aoi[0])), outputFolder)
      except Exception as e:
         print(e)
      
   print('\nComplete')
   print("Date and time: ", now.strftime('%H:%M:%S on %A, %B the %dth, %Y'))
   #print('\nCompleted in {}'.format(time.perf_counter() - startT))
   print('#####################################\n')

if __name__ == "__main__":
   print('\nRunning model')
   print('#####################################')
   now = datetime.datetime.now()
   print("Current date and time: ", now.strftime('%H:%M:%S on %A, %B the %dth, %Y'))
   main(sys.argv[1:])