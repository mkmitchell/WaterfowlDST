"""
Module Waterfowl
================
Defines Waterfowlmodel class which is used for storing parameters and doing calculations for the waterfowl decision support tool.
"""
import os, sys, getopt, datetime, logging, arcpy, json, csv, re, time
from functools import wraps
from arcpy import env
from arcpy.arcobjects.arcobjects import SpatialReference
import pandas as pd
import numpy as np
from arcgis.features import FeatureLayer, GeoAccessor, GeoSeriesAccessor
import geopandas as gpd
from pyproj.crs import CRS

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

def make_df(in_table):
    columns = [f.name for f in arcpy.ListFields(in_table)]
    cur = arcpy.da.SearchCursor(in_table,columns)
    rows = (row for row in cur)
    df = pd.DataFrame(rows,columns=columns)
    return df

def calculate_field(df, inDataset, xTable, curclass):
    if int(arcpy.GetCount_management(inDataset)[0]) > 0:
        file_extension = os.path.splitext(xTable)[-1].lower()
        if file_extension == ".json":
          dataDict = json.load(open(xTable))
        else:
          with open(xTable, mode='r') as infile:
            reader = csv.reader(infile)
            dataDict = {rows[0]:rows[1].split(',') for rows in reader}
        reversed_dict = {val: key.replace('_', '') for key in dataDict for val in dataDict[key]}
        df['CLASS'] = df[curclass].map(reversed_dict)    
    return df    

class Waterfowlmodel:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi, aoiname, wetland, kcalTable, crosswalk, demand, urban, binIt, binUnique, extra, fieldtable, scratch):
    """
    Creates a waterfowl model object.
    
    :param aoi: feature dataset of area of interest
    :type aoi: str
    :param aoiname: Name of area of interest
    :type aoiname: str    
    :param wetland: Wetland feature dataset (e.g. National Wetland Inventory)
    :type wetland: str
    :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by hectares]
    :type kcalTable: str
    :param crosswalk: CSV file relating wetland habitat types to kcal csv table
    :type crosswalk: str
    :param demand: NAWCA stepdown Duck Use Days objectives
    :type demand: str
    :param urban: Spatial dataset of impervious and built features 
    :type urban: str    
    :param binIt: Feature dataset of aggregation features (e.g. HUC12 watersheds)
    :type binIt: str
    :param binUnique: Unique field of aggregation feature (e.g. HUC12 ID number)
    :type binUnique: str
    :param extra: List of extra datasets and their corresponding crossover table
    :type extra: str
    :param fieldtable
    :param scratch: Scratch geodatabase location
    :type scratch: str 
    """
    self.scratch = scratch
    self.aoi = self.projAlbers(aoi, 'AOI')
    self.aoiname = aoiname
    self.binIt = self.projAlbers(self.clipStuff(binIt, 'bin'), 'Bin')
    self.binUnique = binUnique
    self.wetland = self.projAlbers(self.clipStuff(wetland, 'wetland'), 'Wetland')
    self.kcalTbl = kcalTable
    self.kcalList = self.getHabList()
    self.crossTbl = crosswalk
    self.demand = self.projAlbers(self.clipStuff(demand, 'demand'), 'Demand')
    self.urban = self.projAlbers(self.clipStuff(urban, 'urban'), 'Urban')
    self.extra = self.processExtra(extra)
    self.mergedenergy = os.path.join(self.scratch, 'MergedEnergy')
    self.protectedMerge = os.path.join(self.scratch, 'MergedProtLands')
    self.protectedEnergy = os.path.join(self.scratch, 'protectedEnergy')
    self.EnergySurplusDeficit = os.path.join(self.scratch, "BinnedEnergyComparison")
    self.energysupply = os.path.join(self.scratch, "EnergySupply")
    self.fieldtable = fieldtable
    self.origDemand = self.demand
    env.workspace = scratch

  def projAlbers(self, inFeature, cat):
    """
    Project spatial feature datasets to Albers Equal Area (WKSID 102003)

    :param inFeature: feature dataset to project to Albers
    :type inFeature: str
    :param cat: Category name used for unique storage and identification
    :type cat: str
    :return outfc: Location of projected feature
    :rtype outfc: str    
    """
    if arcpy.Describe(inFeature).SpatialReference.Name != 102003:
      outfc = os.path.join(self.scratch, cat + '_projected')
      if not (arcpy.Exists(outfc)):
        print('\tProjecting {}'.format(cat + ' layer: ' + inFeature + ' to ' + outfc))
        arcpy.Project_management(inFeature, outfc, arcpy.SpatialReference(102003))
        return outfc
      else:
        logging.info('\tAlready projected to ' + outfc)
        return outfc        
    else:
      print('\tSpatial reference good')
      return inFeature

  def selectBins(self, aoi, bins):
    """
    Selects bins that intersect the AOI.  Incorporated to remove edge effect error.

    :param aoi: Features used as the area of interest to select intersecting bin features.  Feature AOI name
    :type aoi: str
    :param bins: Feature bin name
    :type bins: str
    :return outfc: Location of selected bins feature dataset
    :rtype outfc: str
    """
    logging.info('\tSelecting bins')
    slt = arcpy.SelectLayerByLocation_management(bins, "intersect", aoi)
    arcpy.CopyFeatures_management(slt ,os.path.join(self.scratch, 'selectedBin'))
    self.aoi = os.path.join(self.scratch, 'selectedBin')
    return os.path.join(self.scratch, 'selectedBin')

  def clipStuff(self, inFeature, cat):
    """
    Clips input feature to the area of interest.

    :param inFeature: Feature dataset to clip to AOI
    :type inFeature: str
    :param cat: Category name used for unique storage
    :type cat: str
    :return outfc: Location of clipped feature dataset
    :rtype outfc: str
    """
    outfc = os.path.join(self.scratch, cat + 'clip')
    if arcpy.Exists(outfc):
      #print('\tAlready have {} clipped with aoi'.format(cat))
      logging.info('\tAlready have {} clipped with aoi'.format(cat))
    else:
      print('\tClipping {}'.format(cat + ' layer: ' + inFeature + ' to ' + outfc))
      logging.info("\tClipping features")
      if cat == 'demand':
        print('\tDemand feature layer')
        arcpy.MakeFeatureLayer_management(in_features=inFeature, out_layer=outfc + 'tLayer', where_clause="", workspace="", field_info="OBJECTID OBJECTID VISIBLE NONE;Shape Shape VISIBLE NONE;SQMI SQMI VISIBLE NONE;ACRE ACRE VISIBLE NONE;ICP ICP VISIBLE NONE;LCP LCP VISIBLE NONE;BCR BCR VISIBLE NONE;JV JV VISIBLE NONE;species species VISIBLE NONE;fips fips VISIBLE NONE;CODE CODE VISIBLE NONE;LTADUD LTADUD VISIBLE RATIO;X80DUD X80DUD VISIBLE RATIO;LTAPopObj LTAPopObj VISIBLE RATIO;X80PopObj X80PopObj VISIBLE RATIO;LTADemand LTADemand VISIBLE RATIO;X80Demand X80Demand VISIBLE RATIO;REGION REGION VISIBLE NONE;Shape_Leng Shape_Leng VISIBLE NONE;Shape_Length Shape_Length VISIBLE NONE;Shape_Area Shape_Area VISIBLE NONE")
        inFeature = outfc + 'tLayer'
      # Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
      # The following inputs are layers or table views: "EnergyDemand"
      arcpy.Clip_analysis(inFeature, self.aoi, outfc)
    return outfc

  def getHabList(self):
    """
    Reads the objects input kcal table and returns a list of habitat types.

    :return list: List of habitat types
    :rtype list: list
    """    
    df = pd.read_csv(self.kcalTbl)
    return list(df['habitatType'])

  def processExtra(self, extra):
    """
    Process all extra energy datasets and returns a Dictionary.

    :param extra: Feature to project to Albers
    :type extra: list
    :return readyExtra: Dictionary of data location as keys and cross class table as value
    :rtype readyExtra: dict
    """
    readyExtra = {}
    a=0
    for k in extra.keys():
      readyExtra[a] = [self.projAlbers(self.clipStuff(extra[k][0], 'extra' + str(a)), 'extra' + str(a)),extra[k][1]]
      a+=1
    return readyExtra

  def crossClass(self, inDataset, xTable, curclass='ATTRIBUTE'):
    """
    Adds a CLASS field to the input dataset and sets it equal to the class field in the crossclass table.

    :param inDataset: Feature to be updated with a new 'CLASS' field
    :type inDataset: str
    :param xTable: Location of csv or json file with two columns, original class and the class it's changing to
    :type xTable: str
    :param curclass: Field that lists current class within inDataset
    :type curclass: str.
    """
    logging.info("Calculating habitat")
    if int(arcpy.GetCount_management(inDataset)[0]) > 0:
      if len(arcpy.ListFields(inDataset,'CLASS'))>0:
        for field in arcpy.ListFields(inDataset):
          if field.name == 'CLASS' and not field.type == 'String':
            arcpy.DeleteField_management(inDataset, 'CLASS')
            arcpy.AddField_management(inDataset, 'CLASS', "TEXT", 50)
      else:
        arcpy.AddField_management(inDataset, 'CLASS', "TEXT", 50)
      # Read data from file:
      file_extension = os.path.splitext(xTable)[-1].lower()
      if file_extension == ".json":
        dataDict = json.load(open(xTable))
      else:
        with open(xTable, mode='r') as infile:
          reader = csv.reader(infile)
          dataDict = {rows[0]:rows[1].split(',') for rows in reader}
      print(inDataset)
      with arcpy.da.UpdateCursor(inDataset, [curclass, 'CLASS']) as cursor:
        for row in cursor:
          if row[0]:
            if row[1] is None or row[1].strip() == '':
              for key, value in dataDict.items():
                if row[0].replace(',', '') in value:
                  row[1] = key.replace('_', '')
                  try:
                    cursor.updateRow(row)
                  except Exception as e:
                    print(e)
                    print(row[0])
                    print(row[1])
                    print(type(row[1]))
                    sys.exit()
            else:
              continue
          else:
            continue
    else:
      return
  
  def supaCrossClass(self, inDataset, xTable, curclass='ATTRIBUTE'):
    df = make_df(inDataset)
    outdf = calculate_field(df, inDataset, xTable, curclass)
    #print(outdf.head())
    outdf = outdf[['OBJECTID', 'CLASS']]
    v = outdf.reset_index()
    outnp = np.rec.fromrecords(v, names=v.columns.tolist())
    if len(arcpy.ListFields(inDataset,'CLASS'))>0:
      arcpy.DeleteField_management(inDataset, 'CLASS')
    if len(arcpy.ListFields(inDataset,'index'))>0:
      arcpy.DeleteField_management(inDataset, 'index')         
    arcpy.da.ExtendTable(inDataset, "OBJECTID", outnp, "OBJECTID")
    return inDataset  

  def joinEnergy(self, wetland, extra, mergedenergy):
    """
    Joins energy layers (Wetland with extra) by merging extra layer datasets and erasing from NWI then merging.

    :param wetland: location of wetland dataset
    :type wetland: str
    :param extra: Location of the extra habitat supply datasets
    :type extra: str    
    :param mergedenergy: Merged energy feature location
    :type mergedenergy: str
    :return: Merged energy feature location
    :rtype: str
    """    
    #Merge extra datasets and erase from NWI then merge
    if arcpy.Exists(mergedenergy):
      logging.info('\tAlready joined habitat supply')
      return mergedenergy
    blah = [item[0] for item in extra.values()]
    print(blah)
    arcpy.analysis.Union(' #;'.join([str(x) for x in blah]) + ' #', os.path.join(self.scratch, 'mergedExtra'), "ALL", None, "GAPS")
    #arcpy.Merge_management(blah, os.path.join(self.scratch, 'mergedExtra'))
    #arcpy.RepairGeometry_management(os.path.join(self.scratch, 'mergedExtra'))
    print('timetoerase')
    arcpy.Erase_analysis(wetland, os.path.join(self.scratch, 'mergedExtra'), os.path.join(self.scratch, 'nwiDelExtra'))
    erased = [os.path.join(self.scratch, 'nwiDelExtra'), os.path.join(self.scratch, 'mergedExtra')]
    arcpy.Merge_management(erased, mergedenergy)
    return mergedenergy

  def prepEnergyFast(self, inDataset, xTable):
    """
    Calculates habitat area and energy of the input dataset

    :param inDataset: Feature to be updated with kcal values that relate to the class
    :type inDataset: str
    :param xTable: Location of csv or json file with two columns, from class and to class
    :type xTable: str
    :return: Modifed inDataset
    :rtype: str
    """
    print('\tCalculate energy for', inDataset)
    logging.info("Calculate energy for " + inDataset)
    if not len(arcpy.ListFields(inDataset,'avalNrgy'))>0:
      arcpy.AddField_management(inDataset, 'avalNrgy', "DOUBLE", 9, "", "", "AvailableEnergy")    
    if not len(arcpy.ListFields(inDataset,'kcal'))>0:
      arcpy.AddField_management(inDataset, 'kcal', "LONG")
    if not len(arcpy.ListFields(inDataset,'CalcHA'))>0:
      arcpy.AddField_management(inDataset, 'CalcHA', "DOUBLE", 9, 2, "", "Hectares")
    arcpy.CalculateGeometryAttributes_management(inDataset, "CalcHA AREA", area_unit="HECTARES")      
    # Read data from file:
    print('\tReading in habitat file')
    file_extension = os.path.splitext(xTable)[-1].lower()
    if file_extension == ".json":
      dataDict = json.load(open(xTable))
    else:
      with open(xTable, mode='r') as infile:
        reader = csv.reader(infile)
        dataDict = {rows[0]:rows[1].split(',') for rows in reader}
    print('\tCalculating available energy')
    with arcpy.da.UpdateCursor(inDataset, ['kcal', 'CLASS', 'avalNrgy', 'CalcHA']) as cursor:
      for row in cursor:
        if row[0] is None:
          for key, value in dataDict.items():
            try:
              if row[1] == key:
                row[0] = value[0]
                row[2] = float(value[0]) * float(row[3])
                cursor.updateRow(row)
            except Exception as e:
              print(e)
              print(key)
              print(value)
              print(value[0])
              print(row[3])
              sys.exit()
        else:
          continue
    del cursor, row
    return inDataset

  def dstOutput(self, mergebin, dissolveFields, outputgdb):
    """
    Runs energy difference between NAWCA stepdown objectives and available habitat.

    :param mergebin: List that holds all datasets to be merged for output
    :type mergebin: list
    :param dissolveFields: Unique field that all features are joined by
    :type dissolveFields: str
    :param outputgdb: Output gdb that will be zipped and shipped
    :type outputgdb: str   
    :return: Shapefile containing model results at the county level
    :rtype: str
    """
    if arcpy.Exists(os.path.join(self.scratch, 'AllDataBintemp')):
      arcpy.Delete_management(os.path.join(self.scratch, 'AllDataBintemp'))
    arcpy.Merge_management(mergebin, os.path.join(self.scratch, 'AllDataBintemp'))
    """
    Energy supply
    Total habitat energy within huc - THabNrg
    Total habitat hectares within huc - THabHA

    Energy demand
        LTA and X80 DUD by huc - TLTADUD anc X80DUD
        LTA and X80 Demand by huc - TLTADemand and X80Demand
        LTA and X80 Population objective by huc - LTAPopObj and X80PopObj
        
    Protected lands
        Total protected hectares by huc - ProtHA

    Protected habitat hectares and energy
        Total protected hectares - ProtHabHA
        Total protected energy - ProtHabNrg

    Weighted mean and calculations based off of it
        Weighted mean kcal/ha with weight being Total habitat energy
        Energy Protection needed - NrgProtRq
        Restoration HA based off of weighted mean - RstorHA
        Protection HA based off weighted mean - RstorProtHA  
    """
    print('\tDissolving features and fixing fields')
    fields = self.binUnique[1] +" MAX; BinHA SUM; UrbanHA SUM; THabNrg SUM;THabHA SUM;LTADUD SUM;LTADemand SUM; LTAPopObj SUM;X80DUD SUM;X80Demand SUM; X80PopObj SUM;ProtHA SUM;ProtHabHA SUM;ProtHabNrg SUM;LTASurpDef SUM;X80SurpDef SUM;wtMeankcal MEAN;"
    if arcpy.Exists(os.path.join(self.scratch, 'AllDataBin')):
      arcpy.Delete_management(os.path.join(self.scratch, 'AllDataBin'))
    #print(fields)
    if not len(arcpy.ListFields(os.path.join(self.scratch, 'AllDataBintemp'),self.binUnique[1]))>0:
      print(self.binUnique[1] + " doesn't exist.  Need to append")
      addHuc = arcpy.da.FeatureClassToNumPyArray(self.binIt, [self.binUnique[0], self.binUnique[1]], null_value='')
      arcpy.da.ExtendTable(os.path.join(self.scratch, 'AllDataBintemp'), self.binUnique[0], addHuc, self.binUnique[0])
    if not len(arcpy.ListFields(os.path.join(self.scratch, 'AllDataBintemp'),'BinHA'))>0:
      arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBintemp'), 'BinHA', "DOUBLE", 9, 2, "", "Hectares")      
    arcpy.CalculateGeometryAttributes_management(os.path.join(self.scratch, 'AllDataBintemp'), "BinHA AREA", area_unit="HECTARES")
    print([f.name for f in arcpy.ListFields(os.path.join(self.scratch, 'AllDataBintemp'))])
    arcpy.Dissolve_management(in_features=os.path.join(self.scratch, 'AllDataBintemp'), out_feature_class=os.path.join(self.scratch, 'AllDataBin'), dissolve_field=self.binUnique[0], statistics_fields=fields, multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'MAX_'+ self.binUnique[1], self.binUnique[0] + 'name', self.binUnique[0] + ' Name')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_BinHA', self.binUnique[0]+ '_ha', self.binUnique[0] +' Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_UrbanHA', 'UrbanHA', 'Urban Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_THabNrg', 'tothabitat_kcal', 'Total Habitat Energy (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_THabHA', 'tothabitat_ha', 'Total Habitat Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_LTADUD', 'dud_lta', 'Long-Term Average Duck Use Days')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_LTADemand', 'demand_lta_kcal', 'Long Term Average Energy Demand (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_LTAPopObj', 'popobj_lta', 'Long Term Average Population Objective')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_X80DUD', 'dud80th', '80th Percentile Duck Use Days')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_X80Demand', 'demand_80th', '80th Percentile Energy Demand (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_X80PopObj', 'popobj_80th', '80th Percentile Population Objective')    
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_ProtHA', 'protected_ha', 'Protected Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_ProtHabHA', 'protectedhabitat_ha', 'Protected Habitat Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_ProtHabNrg', 'protected_kcal', 'Protected Habitat Energy (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_LTASurpDef', 'surpdef_lta_kcal', 'LTA Energy Surplus or Deficit (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_X80SurpDef', 'surpdef_80th_kcal', 'X80 Energy Surplus or Deficit (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'MEAN_wtMeankcal', 'wtMean_kcal_per_ha', 'Weighted mean (kcal)')
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'available_ha', "DOUBLE", 9, 2, "", "Potentiallyl Available Habitat Hectares (Bin HA - Urban HA - Protected HA)")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='available_ha', expression="!" + self.binUnique[0] + "_ha! - !UrbanHA! - !protected_ha!", expression_type="PYTHON_9.3", code_block="")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'nrgprot_lta_kcal', "DOUBLE", 9, 2, "", "LTA Energy Protection Needed (Habitat Energy demand - protected habitat energy) (kcal)")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'nrgprot_80th_kcal', "DOUBLE", 9, 2, "", "X80 Energy Protection Needed (Habitat Energy demand - protected habitat energy) (kcal)")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='nrgprot_lta_kcal', expression="!demand_lta_kcal! - !protected_kcal! if !demand_lta_kcal! - !protected_kcal! > 0 else 0", expression_type="PYTHON_9.3", code_block="")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='nrgprot_80th_kcal', expression="!demand_80th! - !protected_kcal! if !demand_80th! - !protected_kcal! > 0 else 0", expression_type="PYTHON_9.3", code_block="")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'restoregoal_lta_ha', "DOUBLE", 9, 2, "", "LTA Restoration HA based off weighted mean (Surplus/weighted mean)")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'restoregoal_80th_ha', "DOUBLE", 9, 2, "", "X80 Restoration HA based off weighted mean (Surplus/weighted mean)")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='restoregoal_lta_ha', expression="abs(!surpdef_lta_kcal!/!wtMean_kcal_per_ha!) if !surpdef_lta_kcal! < 0 else 0", expression_type="PYTHON_9.3", code_block="")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='restoregoal_80th_ha', expression="abs(!surpdef_80th_kcal!/!wtMean_kcal_per_ha!) if !surpdef_80th_kcal! < 0 else 0", expression_type="PYTHON_9.3", code_block="")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'protectgoal_lta_ha', "DOUBLE", 9, 2, "", "Protection HA based off weighted mean (Energy protected needed/weighted mean)")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'protectgoal_80th_ha', "DOUBLE", 9, 2, "", "X80 Protection HA based off weighted mean (Energy protected needed/weighted mean)")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='protectgoal_lta_ha', expression="(!nrgprot_lta_kcal!/!wtMean_kcal_per_ha!) if !nrgprot_lta_kcal! > 0 else 0", expression_type="PYTHON_9.3", code_block="")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='protectgoal_80th_ha', expression="(!nrgprot_80th_kcal!/!wtMean_kcal_per_ha!) if !nrgprot_80th_kcal! > 0 else 0", expression_type="PYTHON_9.3", code_block="")    
    arcpy.FeatureClassToFeatureClass_conversion(os.path.join(self.scratch, 'AllDataBin'),self.scratch,self.aoiname+'_Output',self.binUnique[0] + " <> ''")
    if arcpy.Exists(os.path.join(outputgdb, self.aoiname+'_Output')):
      arcpy.Delete_management(os.path.join(outputgdb, self.aoiname+'_Output'))
    arcpy.Copy_management(os.path.join(self.scratch, self.aoiname+'_Output'), os.path.join(outputgdb, self.aoiname+'_Output')) 
    return os.path.join(outputgdb, self.aoiname+'_Output')

  def mergeForWeb(self, mainModel, spEnergy, habPct, outputgdb):
    """
    Merges the main model output with species specific energy and habitat percentages for a clean model to web pipeline.

    :param mainModel: Protection and restoration goals dataset
    :type mainModel: str
    :param spEnergy: Species specific goals dataset
    :type spEnergy: str
    :param habPct: Habitat percentage dataset
    :type habPct: str        
    :return: Shapefile containing ready for web output to be zipped
    :rtype: str
    """
    spDict = {'abdu':'American Black Duck', 'amwi':'American Wigeon', 'bwte':'Blue-winged teal', 'gadw':'Gadwall', 'agwt':'Green-winged teal', 'mall':'Mallard', 'nopi':'Northern Pintain', 'nsho':'Northern Shoveler', 'wodu':'Wood duck'}
    #{old field name: [new field name, alias]}
    energDict = {'ltadud':['dud_lta','{} Duck Use Days'], 'lta_pop_obj':['popobj_lta','{} Population Objective'],'lta_demand':['demand_lta_kcal','{} Long-Term Average Energy Demand (kcal)'], 'x80_dud':['dud_80th','{} 80th Percentile Duck Use Days'], 'x80_pop_obj':['popobj_80th', '{} 80th Percentile Population Objective', '80th percentile daily number of {}s that should be supported in the watershed, based on NAWMP Population goals stepped down from county to HUC12 watershed.'],'x80_demand':['demand_80th_kcal','{} 80th Percentile Energy Demand (kcal)']}
    webReady = os.path.join(self.scratch, self.aoiname+ '_WebReady')
    if arcpy.Exists(webReady):
      arcpy.Delete_management(os.path.join(self.scratch, self.aoiname+ '_WebReady'))
    else:
      pass
    arcpy.CopyFeatures_management(mainModel, webReady)
    try:  
      arcpy.management.JoinField(webReady, 'HUC12name', spEnergy, 'huc12', ['mall_ltadud', 'mall_lta_pop_obj', 'mall_lta_demand', 'mall_x80_dud', 'mall_x80_pop_obj', 'mall_x80_demand', 'wodu_ltadud', 'wodu_lta_pop_obj', 'wodu_lta_demand', 'wodu_x80_dud', 'wodu_x80_pop_obj', 'wodu_x80_demand', 'agwt_ltadud', 'agwt_lta_pop_obj', 'agwt_lta_demand', 'agwt_x80_dud', 'agwt_x80_pop_obj', 'agwt_x80_demand', 'amwi_ltadud', 'amwi_lta_pop_obj', 'amwi_lta_demand', 'amwi_x80_dud', 'amwi_x80_pop_obj', 'amwi_x80_demand', 'bwte_ltadud', 'bwte_lta_pop_obj', 'bwte_lta_demand', 'bwte_x80_dud', 'bwte_x80_pop_obj', 'bwte_x80_demand', 'gadw_ltadud', 'gadw_lta_pop_obj', 'gadw_lta_demand', 'gadw_x80_dud', 'gadw_x80_pop_obj', 'gadw_x80_demand', 'nopi_ltadud', 'nopi_lta_pop_obj', 'nopi_lta_demand', 'nopi_x80_dud', 'nopi_x80_pop_obj', 'nopi_x80_demand', 'nsho_ltadud', 'nsho_lta_pop_obj', 'nsho_lta_demand', 'nsho_x80_dud', 'nsho_x80_pop_obj', 'nsho_x80_demand', 'abdu_ltadud', 'abdu_lta_pop_obj', 'abdu_lta_demand', 'abdu_x80_dud', 'abdu_x80_pop_obj', 'abdu_x80_demand'])
      arcpy.management.JoinField(webReady, 'HUC12name', habPct, 'huc12', ['HighSaltMarsh', 'LowSaltMarsh', 'FreshMarsh', 'ManagedFreshMarsh', 'ManagedFreshShallowOpenWater', 'FreshShallowOpenWater', 'FreshShores', 'MudflatSalt', 'SaltMarshNonDominant', 'DeepwaterFresh', 'Subtidal', 'FreshwaterWoody', 'FreshwaterAquaticBed', 'SaltwaterAquaticBed', 'SaltwaterWoody', 'Phragmites', 'ManagedFreshAquaticBed'])
    except Exception as e:
      print(e)
      exit()

    for sp, spname in spDict.items():
      for fldname, fldlst in energDict.items():
        #print('{} will become {}'.format(sp+'_'+fldname, sp + '_' + fldlst[0]))
        arcpy.AlterField_management(webReady, sp+'_'+fldname, sp + '_' + fldlst[0], spname + ' ' + fldlst[1])
    
    for shp in [mainModel, spEnergy, habPct, webReady]:
      #print('\n'+ shp)
      #print([f.name for f in arcpy.ListFields(shp)])
    if arcpy.Exists(os.path.join(outputgdb, self.aoiname+'_WebReady')):
      arcpy.Delete_management(os.path.join(outputgdb, self.aoiname+'_WebReady'))
    arcpy.Copy_management(webReady, os.path.join(outputgdb, self.aoiname+'_WebReady')) 
    return

  def unionEnergy(self, supply, demand):
    """
    Merges supply and demand energy features into one feature to calculate energy surplus or deficit.

    :param supply: Energy supply dataset
    :type supply: str
    :param demand: Energy demand dataset
    :type demand: str    
    :return: Shapefile containing model results at the county level
    :rtype: str
    """
    if arcpy.Exists(self.EnergySurplusDeficit):
      arcpy.Delete_management(self.EnergySurplusDeficit)
    arcpy.Union_analysis([supply, demand], self.EnergySurplusDeficit)
    if not len(arcpy.ListFields(self.EnergySurplusDeficit,'LTASurpDef'))>0:
      print('\tCalculating Surplus/Deficit')
      arcpy.AddField_management(self.EnergySurplusDeficit, 'LTASurpDef', "DOUBLE", 9, 2, "", "LTA EnergySurplusDeficit")
      arcpy.AddField_management(self.EnergySurplusDeficit, 'X80SurpDef', "DOUBLE", 9, 2, "", "X80 EnergySurplusDeficit")
    else:
      print('\Surplus/Deficit exists')
    arcpy.CalculateField_management(self.EnergySurplusDeficit, 'LTASurpDef', "!THabNrg! - !LTADemand!", "PYTHON3")
    arcpy.CalculateField_management(self.EnergySurplusDeficit, 'X80SurpDef', "!THabNrg! - !X80Demand!", "PYTHON3")
    return self.EnergySurplusDeficit

  def aggproportion(self, aggTo, aggData, IDField, aggFields, dissolveFields, scratch, cat,aggStat = 'SUM'):
    """
    Calculates proportional sum aggregate based on area within specified columns of a given dataset to features from another dataset.

    :param aggTo: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type aggTo: str
    :param aggData: Spatial data to be aggregated
    :type aggData: str
    :param IDField: ID field used for data aggregation
    :type IDField: str
    :param aggFields: Field for aggregation
    :type aggFields: str
    :param dissolveFields: Field for dissolving bins after union
    :type dissolveFields: str
    :param scratch: Scratch geodatabase location
    :type scratch: str  
    :param cat: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type cat: str
    :param aggStat: Aggregation statistic.  Default is SUM
    :type aggStat: str    
    :return: Spatial Sum aggregate of aggData within supplied bins
    :rtype:  str
    """
    # Script arguments
    try:
      print('\tProportional aggregation for ' + cat)
      FieldsToAgg = IDField + ' ' + IDField + ' VISIBLE NONE;'
      AggStats = ''
      for a in aggFields:
          FieldsToAgg = FieldsToAgg + a + ' ' + a + ' VISIBLE RATIO;'
          AggStats = AggStats +  a + ' ' + aggStat + ';'
      Dissolve_Field_s_ = dissolveFields
      # Local variables:
      outLayer = os.path.join(scratch, 'aggproptemp' + cat)
      outLayerI = os.path.join(scratch, 'aggUnion' + cat)
      aggToOut = os.path.join(scratch, 'aggTo' + cat)
      # Process: Make Feature Layer
      if arcpy.Exists(aggToOut):
        logging.info('\tAlready dissolved and aggregated everything for ' + cat)
        print('\tAlready dissolved and calculated, returning input')
        return aggToOut
      else:
        arcpy.MakeFeatureLayer_management(in_features=aggData, out_layer=outLayer,field_info=FieldsToAgg)
        arcpy.Union_analysis(in_features=aggTo + ' #;' + outLayer, out_feature_class=outLayerI, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
      arcpy.Dissolve_management(in_features=outLayerI, out_feature_class=aggToOut, dissolve_field=Dissolve_Field_s_, statistics_fields=AggStats, multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
      arcpy.Delete_management(outLayerI)
    except Exception as e:
      print(e)
    return aggToOut

  def aggByField(self, mergeAll, scratch, demand, binme, cat):
    """
    Aggregates energy demand on a smaller scale to multple larger scale features.  Example: County to HUC12.

    :param mergeAll: Merged energy returned from self.prepnpptables.
    :type mergeAll: str
    :param scratch: Scratch geodatabase location
    :type scratch: str  
    :param cat: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type cat: str
    :return: Feature class with energy demand proportioned to smaller aggregation unit based on available energy supply
    :rtype:  str
    """
    try:
      print('\tProportioning energy demand based on energy supply.')
      outLayer = os.path.join(scratch, 'aggByField' + cat)
      #print('\toutlayer:', outLayer)
      print('\tCalculating stats')
      arcpy.Statistics_analysis(in_table=mergeAll, out_table=outLayer + 'hucfipsum', statistics_fields="avalNrgy SUM", case_field="huc12;fips")
      arcpy.Statistics_analysis(in_table=outLayer + 'hucfipsum', out_table=outLayer + 'fipsum', statistics_fields="SUM_avalNrgy SUM", case_field="fips")
      arcpy.AddField_management(outLayer + 'hucfipsum', "PropPCT", "DOUBLE", 9, "", "", "EnergyProportionPercent", "NULLABLE", "REQUIRED")
      arcpy.AddField_management(outLayer + 'hucfipsum', 'hucfip', "TEXT", 50)
      arcpy.CalculateField_management(outLayer + 'hucfipsum', "hucfip", "!huc12!+ !fips!", "PYTHON3", '', "TEXT")
      hucfip = arcpy.AddJoin_management(in_layer_or_view=outLayer + 'hucfipsum', in_field="fips", join_table=outLayer + 'fipsum', join_field="fips", join_type="KEEP_ALL")
      #print('\tjoined - printing field names')
      arcpy.CalculateField_management(in_table=hucfip, field="PropPCT", expression="(!aggByField" + cat + "hucfipsum.SUM_avalNrgy!/!aggByField" + cat + "fipsum.SUM_SUM_avalNrgy!)", expression_type="PYTHON_9.3", code_block="")
      print('\tUnion huc and fips and calculate demand')
      unionme = ' #; '.join([demand, binme]) + ' #'
      arcpy.Union_analysis(in_features=unionme, out_feature_class=outLayer + 'unionhucfips', join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
      arcpy.AddField_management(outLayer + 'unionhucfips', 'hucfip', "TEXT", 50)
      arcpy.CalculateField_management(in_table=outLayer + 'unionhucfips', field="hucfip", expression="!huc12!+ !fips!", expression_type="PYTHON_9.3", code_block="")
      unionhucfip = arcpy.AddJoin_management(in_layer_or_view=outLayer + 'unionhucfips', in_field="hucfip", join_table=outLayer + 'hucfipsum', join_field="hucfip", join_type="KEEP_ALL")
      arcpy.CalculateField_management(in_table=unionhucfip, field='LTADUD', expression="!aggByField" + cat + "unionhucfips.LTADUD! * !aggByField" + cat + "hucfipsum.PropPCT!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=unionhucfip, field='LTAPopObj', expression="!aggByField" + cat + "unionhucfips.LTAPopObj! * !aggByField" + cat + "hucfipsum.PropPCT!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=unionhucfip, field='LTADemand', expression="!aggByField" + cat + "unionhucfips.LTADemand! * !aggByField" + cat + "hucfipsum.PropPCT!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=unionhucfip, field='X80DUD', expression="!aggByField" + cat + "unionhucfips.X80DUD! * !aggByField" + cat + "hucfipsum.PropPCT!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=unionhucfip, field='X80PopObj', expression="!aggByField" + cat + "unionhucfips.X80PopObj! * !aggByField" + cat + "hucfipsum.PropPCT!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=unionhucfip, field='X80Demand', expression="!aggByField" + cat + "unionhucfips.X80Demand! * !aggByField" + cat + "hucfipsum.PropPCT!", expression_type="PYTHON_9.3", code_block="")      
      print('\tDissolve and alter field names')
      #print(self.binUnique)
      arcpy.Dissolve_management(in_features=outLayer + 'unionhucfips', out_feature_class=outLayer+'dissolveHUC', dissolve_field=self.binUnique, statistics_fields="LTADUD SUM;LTAPopObj SUM;LTADemand SUM;X80DUD SUM;X80PopObj SUM;X80Demand SUM", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_LTADUD', 'LTADUD', 'Long term average Duck use days')
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_LTAPopObj', 'LTAPopObj', 'Long term average Population objective')
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_LTADemand', 'LTADemand', 'Long term average energy demand (kcal)')
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_X80DUD', 'X80DUD', 'Long term average Duck use days')
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_X80PopObj', 'X80PopObj', 'Long term average Population objective')
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_X80Demand', 'X80Demand', 'Long term average energy demand (kcal)')      
      return outLayer+'dissolveHUC'
    except Exception as e:
      print(e)
      exc_type, exc_obj, exc_tb = sys.exc_info()
      fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
      print(exc_type, fname, exc_tb.tb_lineno)
      sys.exit()

  def summarizebySpecies(self, demand, scratch, binIt, binUnique, mergedAll, fieldtable):
    """
    Aggregates species specific energy demand on a smaller scale to multiple larger scale features.  Example: County to HUC12.
    Requires original demand layer.

    :param demand: Energy demand layer
    :type demand: str
    :param scratch: Scratch geodatabase location
    :type scratch: str  
    :param binIt: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type binIt: str
    :param mergeAll: Merged energy returned from self.prepnpptables.
    :type mergeAll: str
    :fieldtable: ModelOutputFieldDictionary.csv, contains crosswalk from original field names to correct field names and aliases.
    :return: Feature class with energy demand proportioned to smaller aggregation unit based on available energy supply
    :rtype:  str
    """
    print(demand)
    print(binIt)
    print(binUnique)
    # Create a feature class with all the bin unique values
    spRef = arcpy.Describe(mergedAll).spatialReference
    Joined_demandbySpecies = os.path.join(scratch, 'demandbySpecies')
    arcpy.CreateFeatureclass_management(scratch, "demandbySpecies", geometry_type='POLYGON', spatial_reference=spRef)
    for uni in binUnique:
      arcpy.AddField_management(Joined_demandbySpecies, uni, "TEXT")
    arcpy.Append_management(binIt, Joined_demandbySpecies, "NO_TEST")

    # read in csv that contains the crosswalk for all the field names
    fieldtable = pd.read_csv(fieldtable, encoding='unicode_escape')

    # species list
    fieldtable["species"]=fieldtable["species"].apply(str)
    speciesList = [f.upper() for f in fieldtable.species.unique() if f.upper()!='ALL']

    print("Field Table: ", speciesList)

  def energyBySpecies(self, demand, scratch, binIt, mergedAll):
    """
    Runs species specific energy demand.

    :param demand: Energy demand layer
    :type demand: str
    :param scratch: Scratch geodatabase location
    :type scratch: str  
    :param binIt: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type binIt: str
    :param mergeAll: Merged energy returned from self.prepnpptables.
    :type mergeAll: str      
    """
    insp = gpd.GeoDataFrame.from_file(arcpy.Describe(demand).path, layer=arcpy.Describe(demand).name)
    speciesList = insp.species.unique()
    try:
      speciesList = speciesList[~np.in1d(speciesList, np.array(['All']))]
    except:
      pass
    print(speciesList)
    for sp in speciesList:
      # filter demand layer to only this species...
      print(sp)
      selectDemand = arcpy.SelectLayerByAttribute_management(in_layer_or_view=demand, selection_type="NEW_SELECTION", where_clause="species = '{}'".format(sp))
      # if records for this species exist..
      if int(arcpy.management.GetCount(selectDemand)[0]) > 0:
        # create a copy of the demand layer for this species
        demandSelected = os.path.join(scratch, 'EnergyDemandSelected_{}'.format(sp))
        arcpy.CopyFeatures_management(selectDemand, os.path.join(scratch, demandSelected))
        print("\tAggregating energy demand on a smaller scale to multiple larger scale features for each species.  Example: County to HUC12.")
        demandbySpecies = self.aggByField(mergedAll, scratch, demandSelected, binIt, sp)
        #print(demandbySpecies)
        print("Records in aggbyfield output", int(arcpy.GetCount_management(demandbySpecies)[0]))
        insp = pd.DataFrame.spatial.from_featureclass(demandbySpecies)
        for col in insp.columns[3:-1]:
            insp.rename(columns={col: sp+'_'+col}, inplace = True)
        print(insp.columns)
        for dropme in ['OBJECTID', 'species', 'CODE']:
          try:
            insp.drop(dropme, axis=1, inplace=True)
          except:
            pass
        if sp == speciesList[0]:
            outdf = insp
        else:
            insp.drop(['SHAPE', 'name'], axis=1, inplace=True)
            outdf = outdf.join(insp.set_index('huc12'), on='huc12', how='left', rsuffix=sp)
    if arcpy.Exists(os.path.join(scratch, 'DemandBySpecies')):
      arcpy.Delete_management(os.path.join(scratch, 'DemandBySpecies'))
    outdf.spatial.to_featureclass(os.path.join(scratch, 'DemandBySpecies'))
    return os.path.join(scratch, 'DemandBySpecies')

  @report_time
  def calcProtected(self, mergedenergy, protectedMerge, protectedEnergy):
    """
    Creates attribute for hectares of habitat and hectares of protected habitat
    """
    if not arcpy.Exists(protectedEnergy):
      try:
        arcpy.Clip_analysis(mergedenergy, protectedMerge, protectedEnergy)
      except Exception as e:
        print('\t Need to repair')
        sys.exit()
        #arcpy.RepairGeometry_management(mergedenergy)
        #arcpy.RepairGeometry_management(protectedMerge)
        #arcpy.Clip_analysis(mergedenergy, protectedMerge, protectedEnergy)
      arcpy.CalculateField_management(in_table=protectedEnergy, field="CalcHA", expression="!shape.area@hectares!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=protectedEnergy, field="avalNrgy", expression="!CalcHA!* !kcal!", expression_type="PYTHON_9.3", code_block="")

  def prepProtected(self, protlist):
    """
    Prepares protected lands by merging protected features in the passed list.

    :param protlist: Protected feature classes
    :type protlist: list
    """
    if not arcpy.Exists(self.protectedMerge):
      arcpy.analysis.Union(protlist, os.path.join(self.scratch, 'protunion'), "ALL", None, "GAPS")
      arcpy.management.Dissolve(os.path.join(self.scratch, 'protunion'), self.protectedMerge, None, None, "MULTI_PART", "DISSOLVE_LINES")
    if not len(arcpy.ListFields(self.protectedMerge,'CalcHA'))>0:
        arcpy.AddField_management(self.protectedMerge, 'CalcHA', "DOUBLE", 9, 2, "", "GIS Hectares") 
    arcpy.CalculateGeometryAttributes_management(self.protectedMerge, "CalcHA AREA", area_unit="HECTARES")

  @report_time
  def pandasMerge(self, pad, nced, output):
    """
    Prepares protected lands by merging protected features in the passed list.

    :param pad: List of dataset locations to be merged
    :type pad: list
    :param nced: List of dataset locations to be merged
    :type nced: list    
    :param output: Location of output
    :type output: str
    :return output: Location of output
    :rtype output: str    
    """
    pad = gpd.read_file(os.path.dirname(pad), layer=os.path.basename(pad)).buffer(0)
    nced = gpd.read_file(os.path.dirname(nced), layer=os.path.basename(nced)).buffer(0)
    diff = pad.difference(nced).append(nced.geometry)
    #print(output)
    diff.to_file(output)
    if not len(arcpy.ListFields(output,'CalcHA'))>0:
        arcpy.AddField_management(output, 'CalcHA', "DOUBLE", 9, 2, "", "GIS Hectares") 
    arcpy.CalculateGeometryAttributes_management(output, "CalcHA AREA", area_unit="HECTARES")
    return output

  @report_time
  def pandasMergeMulti(self, toMerge, output):
    """
    Prepares protected lands by merging protected features in the passed list.

    :param toMerge: List of dataset locations to be merged
    :type toMerge: list
    :param output: Location of output
    :type output: str
    :return output: Location of output
    :rtype output: str    
    """
    #pad = gpd.read_file(r'D:\GIS\scratch\dst\SouthAtlantic\SouthAtlantic_scratch.gdb', layer='padusaoi')
    #nced = gpd.read_file(r'D:\GIS\scratch\dst\SouthAtlantic\SouthAtlantic_scratch.gdb', layer='ncedaoi')
    #diff = pad.difference(nced).append(nced.geometry)
    #diff.to_file("d:\\gis\\scratch\\pandasmergeBIG.shp")
    diffs = []
    gdfs = []
    for i in toMerge:
      gdfs.append(gpd.read_file(os.path.dirname(i), layer=os.path.basename(i)).buffer(0))
    for idx, gdf in enumerate(gdfs):
      if idx < len(gdfs) - 1:
        diffs.append(gdf.symmetric_difference(gdfs[idx+1]).iloc[0])
    diffs.append(gdfs[-1].iloc[0].geometry)
    diffs.to_file(output)
    if not len(arcpy.ListFields(output,'CalcHA'))>0:
        arcpy.AddField_management(output, 'CalcHA', "DOUBLE", 9, 2, "", "GIS Hectares") 
    arcpy.CalculateGeometryAttributes_management(output, "CalcHA AREA", area_unit="HECTARES")
    return output

  @report_time
  def pandasClean(self, workspace, toClean):
    """
    ESRI Repair is slow.  Pandas buffering by 0 seems to fix irregularities much faster.

    :param workspace: Workspace directory for storing temporary data
    :type workspace: str
    :param toClean: Feature Class that needs repair.
    :type toClean: str
    :return output: Location of output
    :rtype output: str
    """
    print('\tCleaning ' + os.path.basename(toClean))
    output = os.path.join(os.path.dirname(toClean), os.path.basename(toClean) + '_Cleaned')
    cleanMe = gpd.read_file(os.path.dirname(toClean), layer=os.path.basename(toClean))
    cleanMe['geometry'] = cleanMe.buffer(0)
    cleanMe = cleanMe.to_crs(CRS.from_string('EPSG:4326'))
    cleaned = pd.DataFrame.spatial.from_geodataframe(cleanMe)
    cleaned.spatial.to_featureclass(location=output+'toproj')
    arcpy.Project_management(output+'toproj', output, arcpy.SpatialReference(102003))
    return output
  
  @report_time
  def cleanMe(self, toClean):
    arcpy.RepairGeometry_management(toClean)
    return toClean

  def prepnpTables(self, demand, binme, energy, scratch):
    """
    Reads in merged energy dataset, repairs it, then exports a csv file for use in habitat proportion calculations.

    :param demand: Energy demand layer location
    :type demand: str
    :param binme: Bin to aggregate data to
    :type binme: str
    :param energy: Merged energy supply layer
    :type energy: str
    :param scratch: Scratch geodatabase location
    :type scratch: str
    :return: Merged energy supply and demand layer location
    :rtype: str 
    """    
    outLayer = os.path.join(scratch, 'MergeAll')
    #print('\toutlayer:', outLayer)
    unionme = ' #; '.join([demand, binme, energy]) + ' #'
    #print(unionme)
    for fc in [demand, energy]:
       if len(arcpy.ListFields(fc,'name'))>0:
         arcpy.DeleteField_management(fc,["name"])
    if not arcpy.Exists(outLayer):
      print('\tRun union')
      arcpy.Union_analysis(in_features=unionme, out_feature_class=outLayer, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
    #if arcpy.Exists(os.path.join(os.path.dirname(self.scratch),'tbl.csv')):
    #  arcpy.Delete_management(os.path.join(os.path.dirname(self.scratch),'tbl.csv'))
    #arcpy.TableToTable_conversion(in_rows=outLayer, out_path=os.path.dirname(self.scratch), out_name="tbl.csv", where_clause="", field_mapping='avalNrgy "AvailableEnergy" true true false 8 Double 0 0 ,First,#,'+outLayer+',avalNrgy,-1,-1;CLASS "CLASS" true true false 255 Text 0 0 ,First,#,'+outLayer+',CLASS,-1,-1;CalcHA "Hectares" true true false 8 Double 0 0 ,First,#,'+outLayer+',CalcHA,-1,-1;kcal "kcal" true true false 4 Long 0 0 ,First,#,'+outLayer+',kcal,-1,-1;HUC12 "HUC12" true true false 12 Text 0 0 ,First,#,'+outLayer+',HUC12,-1,-1;Shape_Length "Shape_Length" false true true 8 Double 0 0 ,First,#,'+outLayer+',Shape_Length,-1,-1;Shape_Area "Shape_Area" false true true 8 Double 0 0 ,First,#,'+outLayer+',Shape_Area,-1,-1', config_keyword="")
    #arcpy.TableToTable_conversion(in_rows=outLayer, out_path=os.path.dirname(self.scratch), out_name="tbl.csv")
    #print('\tunioned')
    wtmarray = arcpy.da.FeatureClassToNumPyArray(outLayer, ['avalNrgy','CLASS', 'CalcHA', self.binUnique[0], self.binUnique[1], 'kcal'], null_value=0)
    return outLayer, wtmarray

  def pctHabitatType(self, binUnique, wtmarray):
    """
    Calculates proportion of habitat type by bin feature.
    """
    print('\tConverting to pandas')
    #df = pd.read_csv(os.path.join(os.path.dirname(self.scratch),'tbl.csv'), usecols=['avalNrgy','CLASS', 'CalcHA', binUnique, 'kcal'], dtype={'avalNrgy': np.float, 'CLASS':np.string_,'CalcHA':np.float, binUnique:np.string_})
    df = pd.DataFrame(wtmarray)
    df = df.dropna(subset=['CLASS', binUnique, 'kcal'])
    df1 = df.groupby([binUnique]).CalcHA.sum()
    dfmerge = pd.merge(df, df1, on=[binUnique,binUnique],how='left')
    dfmerge['pct'] = (dfmerge['CalcHA_x']/dfmerge['CalcHA_y'])*100
    outdf = dfmerge.pivot_table(index=binUnique, columns='CLASS', values='pct', aggfunc=np.sum)
    outdf = outdf.fillna(0)
    outdf = outdf.drop(columns = ['', 'nan'])
    print(outdf.head())
    #print(outdf.sum(axis=1))
    badfields = []
    for field in self.kcalList:
      try:
        outdf[field] = outdf[field] # Percent only
      except:
        #print('\tNo habitat in aoi:', field)
        badfields.append(field)
        continue
    outdf.to_csv(os.path.join(os.path.dirname(self.scratch),'HabitatPct.csv'), index=True)
    outdf = outdf.reset_index()
    outdf[binUnique] = outdf[binUnique].astype(str)
    outnp = np.array(np.rec.fromrecords(outdf))
    names = outdf.dtypes.index.tolist()
    outnp.dtype.names = tuple(names)
    print(names)
    arcpy.env.overwriteOutput = True
    if arcpy.Exists(os.path.join(self.scratch, 'HabitatPct')):
      arcpy.Delete_management(os.path.join(self.scratch, 'HabitatPct'))
    arcpy.da.NumPyArrayToTable(outnp, os.path.join(self.scratch, 'HabitatPct'))
    arcpy.CopyFeatures_management(os.path.join(self.scratch, 'aggByFieldenergydemanddissolveHUC') ,os.path.join(self.scratch, 'HabitatProportion'))
    for field in self.kcalList:
      if not len(arcpy.ListFields(os.path.join(self.scratch, 'HabitatProportion'),field))>0:
        arcpy.AddField_management(os.path.join(self.scratch, 'HabitatProportion'), field, "DOUBLE")
    joinedhab = arcpy.AddJoin_management(in_layer_or_view=os.path.join(self.scratch, 'HabitatProportion'), in_field="HUC12", join_table=os.path.join(self.scratch, 'HabitatPct'), join_field="HUC12", join_type="KEEP_ALL")
    print('\tCalculating sum of habitat hectares by bin')
    for field in self.kcalList:
      if not field in badfields:
        arcpy.CalculateField_management(joinedhab, field, '!HabitatPct.'+field+'!', "PYTHON3")        
    return os.path.join(self.scratch, 'HabitatProportion')

  def weightedMean(self, inDataset, wtmarray):
    """
    Calculates weighted average of kcal/ha weight available energy as the weight.
    """
    print('\tCalculating  weighted average')
    df = pd.DataFrame(wtmarray)
    df = df.dropna(subset=['CLASS', self.binUnique[0], 'kcal'])
    hucsum = pd.DataFrame(df.groupby([self.binUnique[0]])['avalNrgy'].sum())
    hucclasssum = pd.DataFrame(df.groupby([self.binUnique[0], 'CLASS'])['avalNrgy'].sum())
    calc = hucclasssum.join(hucsum, lsuffix='_main', rsuffix='_sum')
    calc['pct'] = calc['avalNrgy_main']/calc['avalNrgy_sum']
    dfclass = pd.DataFrame(df.groupby([self.binUnique[0], 'CLASS'])['kcal'].mean())
    merge = pd.merge(dfclass, calc, on=[self.binUnique[0], 'CLASS'])
    merge['wtMeankcal'] = merge['kcal'] * merge['pct']
    wtmean = merge.groupby([self.binUnique[0]])['wtMeankcal'].sum()
    wtmean = wtmean.reset_index()
    wtmean.columns = [self.binUnique[0], 'wtMeankcal']
    outnp = np.rec.fromrecords(wtmean.values, names=wtmean.columns.tolist())
    if len(arcpy.ListFields(inDataset,'wtMeankcal'))>0:
      arcpy.DeleteField_management(inDataset, 'wtMeankcal')
    arcpy.da.ExtendTable(inDataset, self.binUnique[0], outnp, self.binUnique[0])
    return


      