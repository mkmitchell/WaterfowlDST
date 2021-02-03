"""
Module Waterfowl
================
Defines Waterfowlmodel class which is used for storing parameters and doing calculations for the waterfowl decision support tool.
"""
import os, sys, getopt, datetime, logging, arcpy, json, csv, re
from arcpy import env
import pandas as pd
import numpy as np
from arcgis.features import FeatureLayer, GeoAccessor

class Waterfowlmodel:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi, aoiname, wetland, kcalTable, crosswalk, demand, binIt, binUnique, extra, scratch):
    """
    Creates a waterfowl model object.
    
    :param aoi: Area of interest
    :type aoi: str
    :param aoiname: Name of AOI
    :type aoiname: str    
    :param wetland: National Wetlands Inventory
    :type wetland: str
    :param kcalTable: CSV file containing two columns [habitat type, kilocalorie value by hectares]
    :type kcalTable: str
    :param crosswalk: CSV file relating wetland habitat types to kcal csv table
    :type crosswalk: str
    :param demand: NAWCA stepdown DUD objectives
    :type demand: str
    :param binIt: Aggregation feature
    :type binIt: str
    :param binUnique: Unique field of aggregation feature
    :type binUnique: str
    :param extra: List of extra datasets and their corresponding crossover table
    :type extra: str    
    :param scratch: Scratch geodatabase location
    :type scratch: str   
    """
    self.scratch = scratch
    self.aoi = self.projAlbers(aoi, 'AOI')
    self.aoiname = aoiname
    self.binIt = self.selectBins(self.aoi, self.projAlbers(binIt, 'bin'))
    self.binUnique = binUnique
    self.wetland = self.projAlbers(self.clipStuff(wetland, 'wetland'), 'Wetland')
    self.kcalTbl = kcalTable
    self.kcalList = self.getHabList()
    self.crossTbl = crosswalk
    self.demand = self.projAlbers(self.clipStuff(demand, 'demand'), 'Demand')
    self.extra = self.processExtra(extra)
    self.mergedenergy = os.path.join(self.scratch, 'MergedEnergy')
    self.protectedMerge = os.path.join(self.scratch, 'MergedProtLands')
    self.protectedEnergy = os.path.join(self.scratch, 'protectedEnergy')
    self.EnergySurplusDeficit = os.path.join(self.scratch, "BinnedEnergyComparison")
    self.energysupply = os.path.join(self.scratch, "EnergySupply")
    env.workspace = scratch

  def projAlbers(self, inFeature, cat):
    """
    Projects in features to Albers Equal Area (WKSID 102003)

    :param inFeature: Feature to project to Albers
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
      logging.info('Already have {} clipped with aoi'.format(cat))
    else:
      print('\tClipping {}'.format(cat + ' layer: ' + inFeature + ' to ' + outfc))
      logging.info("Clipping features")
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
    with arcpy.da.UpdateCursor(inDataset, [curclass, 'CLASS']) as cursor:
      for row in cursor:
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

  def joinEnergy(self, wetland, extra, mergedenergy):
    """
    Joins energy layers (Wetland with extra)

    :param wetland: location of wetland dataset
    :type wetland: str
    :param extra: Location of the extra habitat supply datasets
    :type extra: str    
    :param mergedenergy: Merged energy feature location
    :type mergedenergy: str
    :return: Merged energy feature location
    :rtype: str
    """    
    #Delete Wetland area from each extra dataset
    if arcpy.Exists(mergedenergy):
      logging.info('\tAlready joined habitat supply')
      return mergedenergy
    erased = [wetland]
    for i in extra.keys():
      arcpy.Erase_analysis(extra[i][0], wetland, os.path.join(self.scratch, 'del' + str(i)))
      erased.append(os.path.join(self.scratch, 'del' + str(i)))
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
        LTA DUD by huc - TLTADUD
        LTA Demand by huc - TLTADemand
        
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
    fields = "THabNrg SUM;THabHA SUM;LTADUD SUM;LTADemand SUM;ProtHA SUM;ProtHabHA SUM;ProtHabNrg SUM;SurpDef SUM;wtMeankcal MEAN;"
    #for field in self.kcalList:
      #fields+= field + " MEAN;"
    #print(dissolveFields)
    if arcpy.Exists(os.path.join(self.scratch, 'AllDataBin')):
      arcpy.Delete_management(os.path.join(self.scratch, 'AllDataBin'))
    #print(fields)
    arcpy.Dissolve_management(in_features=os.path.join(self.scratch, 'AllDataBintemp'), out_feature_class=os.path.join(self.scratch, 'AllDataBin'), dissolve_field=dissolveFields, statistics_fields=fields, multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_THabNrg', 'THabNrg', 'Habitat Energy (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_THabHA', 'THabHA', 'Habitat Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_LTADUD', 'TLTADUD', 'Long Term Average Duck Use Days')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_LTADemand', 'TLTADemand', 'Long Term Average Energy Demand (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_ProtHA', 'ProtHA', 'Protected Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_ProtHabHA', 'ProtHabHA', 'Protected Habitat Hectares')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_ProtHabNrg', 'ProtHabNrg', 'Protected Habitat Energy (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'SUM_SurpDef', 'SurpDef', 'Energy Surplus or Deficit (kcal)')
    arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'MEAN_wtMeankcal', 'wtMeankcal', 'Weighted mean (kcal)')
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'NrgProtRq', "DOUBLE", 9, 2, "", "Energy Protection Needed (Habitat Energy demand - protected habitat energy) (kcal)")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='NrgProtRq', expression="!TLTADemand! - !ProtHabNrg! if (TLTADemand! - !ProtHabNrg!) > 0 else 0", expression_type="PYTHON_9.3", code_block="")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'RstorHA', "DOUBLE", 9, 2, "", "Restoration HA based off weighted mean (Surplus/weighted mean)")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='RstorHA', expression="abs(!SurpDef!/!wtMeankcal!) if !SurpDef! < 0 else 0", expression_type="PYTHON_9.3", code_block="")
    arcpy.AddField_management(os.path.join(self.scratch, 'AllDataBin'), 'RstorProtHA', "DOUBLE", 9, 2, "", "Protection HA based off weighted mean (Energy protected needed/weighted mean)")
    arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field='RstorProtHA', expression="(!NrgProtRq!/!wtMeankcal!) if !SurpDef! < 0 else 0", expression_type="PYTHON_9.3", code_block="")    
    #for field in self.kcalList:
      #arcpy.AlterField_management(os.path.join(self.scratch, 'AllDataBin'), 'MEAN_'+field, field, field + 'Percentage')
      #arcpy.CalculateField_management(in_table=os.path.join(self.scratch, 'AllDataBin'), field=field, expression="abs(!SurpDef!) * !"+field+"! if !SurpDef! < 0 else 0", expression_type="PYTHON_9.3", code_block="")
    #arcpy.Copy_management(os.path.join(self.scratch, 'AllDataBin'), os.path.join(self.scratch, self.aoiname+'_Output'))
    arcpy.FeatureClassToFeatureClass_conversion(os.path.join(self.scratch, 'AllDataBin'),self.scratch,self.aoiname+'_Output',self.binUnique + " <> ''")
    if arcpy.Exists(os.path.join(outputgdb, self.aoiname+'_Output')):
      arcpy.Delete_management(os.path.join(outputgdb, self.aoiname+'_Output'))
    arcpy.Copy_management(os.path.join(self.scratch, self.aoiname+'_Output'), os.path.join(outputgdb, self.aoiname+'_Output')) 
    return os.path.join(outputgdb, self.aoiname+'_Output')

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
    if not len(arcpy.ListFields(self.EnergySurplusDeficit,'SurpDef'))>0:
      print('\tAdding SurpDef')
      arcpy.AddField_management(self.EnergySurplusDeficit, 'SurpDef', "DOUBLE", 9, 2, "", "EnergySurplusDeficit")
    else:
      print('\tSurfDef exists')
    arcpy.CalculateField_management(self.EnergySurplusDeficit, 'SurpDef', "!THabNrg! - !LTADemand!", "PYTHON3")
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
      arcpy.CalculateField_management(in_table=outLayer + 'hucfipsum', field="hucfip", expression="!huc12!+ !fips!", expression_type="PYTHON_9.3", code_block="")
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
      print('\tdissolve and alter field names')
      arcpy.Dissolve_management(in_features=outLayer + 'unionhucfips', out_feature_class=outLayer+'dissolveHUC', dissolve_field="huc12", statistics_fields="LTADUD SUM;LTAPopObj SUM;LTADemand SUM", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_LTADUD', 'LTADUD', 'Long term average Duck use days')
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_LTAPopObj', 'LTAPopObj', 'Long term average Population objective')
      arcpy.AlterField_management(outLayer+'dissolveHUC', 'SUM_LTADemand', 'LTADemand', 'Long term average energy demand (kcal)')
      return outLayer+'dissolveHUC'
    except Exception as e:
      print(e)
      exc_type, exc_obj, exc_tb = sys.exc_info()
      fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
      print(exc_type, fname, exc_tb.tb_lineno)
      sys.exit()

  def calcProtected(self):
    """
    Creates attribute for hectares of habitat and hectares of protected habitat
    """
    if not arcpy.Exists(self.protectedEnergy):
      #print('\tClean energy')
      arcpy.RepairGeometry_management(self.mergedenergy)
      arcpy.Clip_analysis(self.mergedenergy, self.protectedMerge, self.protectedEnergy)
      arcpy.CalculateField_management(in_table=self.protectedEnergy, field="CalcHA", expression="!shape.area@hectares!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=self.protectedEnergy, field="avalNrgy", expression="!CalcHA!* !kcal!", expression_type="PYTHON_9.3", code_block="")

  def prepProtected(self, nced, padus):
    """
    Prepares protected lands by merging nced and padus by deleting NCED from PAD and running a union.

    :param nced: NCED feature class
    :type nced: str
    :param padus: PADUS feature class
    :type padus: str
    """
    if not arcpy.Exists(os.path.join(self.scratch, 'delncedfrompad')):
      arcpy.Erase_analysis(padus, nced, os.path.join(self.scratch, 'delncedfrompad'))
    if not arcpy.Exists(self.protectedMerge):
      arcpy.Merge_management([nced, os.path.join(self.scratch, 'delncedfrompad')], self.protectedMerge)
    if not len(arcpy.ListFields(self.protectedMerge,'CalcHA'))>0:
        arcpy.AddField_management(self.protectedMerge, 'CalcHA', "DOUBLE", 9, 2, "", "GIS Hectares") 
    arcpy.CalculateGeometryAttributes_management(self.protectedMerge, "CalcHA AREA", area_unit="HECTARES")      
    
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
    print(unionme)
    if not arcpy.Exists(outLayer):
      print('\tRun union')
      arcpy.Union_analysis(in_features=unionme, out_feature_class=outLayer, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
    if arcpy.Exists(os.path.join(os.path.dirname(self.scratch),'tbl.csv')):
      arcpy.Delete_management(os.path.join(os.path.dirname(self.scratch),'tbl.csv'))
    arcpy.TableToTable_conversion(in_rows=outLayer, out_path=os.path.dirname(self.scratch), out_name="tbl.csv", where_clause="", field_mapping='avalNrgy "AvailableEnergy" true true false 8 Double 0 0 ,First,#,'+outLayer+',avalNrgy,-1,-1;CLASS "CLASS" true true false 255 Text 0 0 ,First,#,'+outLayer+',CLASS,-1,-1;CalcHA "Hectares" true true false 8 Double 0 0 ,First,#,'+outLayer+',CalcHA,-1,-1;kcal "kcal" true true false 4 Long 0 0 ,First,#,'+outLayer+',kcal,-1,-1;HUC12 "HUC12" true true false 12 Text 0 0 ,First,#,'+outLayer+',HUC12,-1,-1;Shape_Length "Shape_Length" false true true 8 Double 0 0 ,First,#,'+outLayer+',Shape_Length,-1,-1;Shape_Area "Shape_Area" false true true 8 Double 0 0 ,First,#,'+outLayer+',Shape_Area,-1,-1', config_keyword="")
    #print('\tunioned')
    return outLayer

  def pctHabitatType(self):
    """
    Calculates proportion of habitat type by bin feature.
    """
    print('\tConverting to pandas')
    df = pd.read_csv(os.path.join(os.path.dirname(self.scratch),'tbl.csv'), usecols=['avalNrgy','CLASS', 'CalcHA', self.binUnique, 'kcal'], dtype={'avalNrgy': np.float, 'CLASS':np.string_,'CalcHA':np.float, self.binUnique:np.string_})
    df = df.dropna(subset=['CLASS', self.binUnique, 'kcal'])
    df1 = df.groupby([self.binUnique]).CalcHA.sum()
    dfmerge = pd.merge(df, df1, on=[self.binUnique,self.binUnique],how='left')
    dfmerge['pct'] = (dfmerge['CalcHA_x']/dfmerge['CalcHA_y'])*100
    outdf = dfmerge.pivot_table(index=self.binUnique, columns='CLASS', values='pct', aggfunc=np.sum)
    outdf = outdf.fillna(0)
    print(outdf.head())
    print(outdf.sum(axis=1))
    badfields = []
    for field in self.kcalList:
      try:
        outdf[field] = outdf[field] # Percent only
      except:
        print('\tProblem with key', field)
        badfields.append(field)
        continue
    outdf.to_csv(os.path.join(os.path.dirname(self.scratch),'HabitatPct.csv'), index=True)
    outdf = outdf.reset_index()
    outdf[self.binUnique] = outdf[self.binUnique].astype(str)
    outnp = np.array(np.rec.fromrecords(outdf))
    names = outdf.dtypes.index.tolist()
    outnp.dtype.names = tuple(names)
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

  def weightedMean(self):
    """
    Calculates weighted average of kcal/ha weight available energy as the weight.
    """
    print('\tCalculating  weighted average')
    df = pd.read_csv(os.path.join(os.path.dirname(self.scratch),'tbl.csv'), usecols=['avalNrgy','CLASS', 'CalcHA', self.binUnique, 'kcal'], dtype={'avalNrgy': np.float, 'CLASS':np.string_,'CalcHA':np.float, self.binUnique:np.string_})
    df = df.dropna(subset=['CLASS', self.binUnique, 'kcal'])
    df['avalNrgy'] = df['avalNrgy'].fillna(0)
    df['CalcHA'] = df['CalcHA'].fillna(0)
    df['kcal'] = df['kcal'].fillna(0)
    hucsum = pd.DataFrame(df.groupby(['HUC12'])['avalNrgy'].sum())
    hucclasssum = pd.DataFrame(df.groupby(['HUC12', 'CLASS'])['avalNrgy'].sum())
    calc = hucclasssum.join(hucsum, lsuffix='_main', rsuffix='_sum')
    calc['pct'] = calc['avalNrgy_main']/calc['avalNrgy_sum']
    dfclass = pd.DataFrame(df.groupby(['HUC12', 'CLASS'])['kcal'].mean())
    merge = pd.merge(dfclass, calc, on=['HUC12', 'CLASS'])
    merge['wtmean'] = merge['kcal'] * merge['pct']
    wtmean = merge.groupby(['HUC12'])['wtmean'].sum()
    wtmean = wtmean.reset_index()
    wtmean.columns = ['HUC12', 'wtmean']
    outnp = np.rec.fromrecords(wtmean.values, names=wtmean.columns.tolist())
    if arcpy.Exists(os.path.join(self.scratch, 'HUCwtMean')):
      arcpy.Delete_management(os.path.join(self.scratch, 'HUCwtMean'))
    arcpy.da.NumPyArrayToTable(outnp, os.path.join(self.scratch, 'HUCwtMean'))
    arcpy.AddField_management(os.path.join(self.scratch, 'aggByFieldenergydemanddissolveHUC'), 'wtMeankcal', "DOUBLE")
    joinedhab = arcpy.AddJoin_management(in_layer_or_view=os.path.join(self.scratch, 'aggByFieldenergydemanddissolveHUC'), in_field="HUC12", join_table=os.path.join(self.scratch, 'HUCwtMean'), join_field="HUC12", join_type="KEEP_ALL")
    arcpy.CalculateField_management(joinedhab, 'wtMeankcal', '!HUCwtMean.wtmean!', "PYTHON3")
    return os.path.join(self.scratch,'aggByFieldenergydemanddissolveHUC')
