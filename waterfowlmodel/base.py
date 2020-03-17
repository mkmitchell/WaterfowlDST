"""
Module Waterfowl
================
Defines Waterfowlmodel class which is initialized by supplying an area of interest shapfile, wetland shapefile, kilocalorie by habitat type table, and the table linking the wetland shapefile to the kcal table.
"""
import os, sys, getopt, datetime, logging, arcpy, json
from arcpy import env

class Waterfowlmodel:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi, wetland, kcalTable, crosswalk, demand, binIt, scratch):
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
    :param demand: NAWCA stepdown DUD objectives
    :type demand: str
    :param bin: Aggregation feature
    :type bin: str    
    :param scratch: Scratch geodatabase location
    :type scratch: str
    """
    self.scratch = scratch
    self.aoi = self.projAlbers(aoi, 'aoi')
    self.wetland = self.projAlbers(self.clipStuff(wetland, 'wetland'), 'wetland')
    self.kcalTbl = kcalTable
    self.crossTbl = crosswalk
    self.demand = self.projAlbers(self.clipStuff(demand, 'demand'), 'demand')
    self.binIt = self.projAlbers(self.clipStuff(binIt, 'bin'), 'bin')
    env.workspace = scratch

  def projAlbers(self, inFeature, cat):
    if arcpy.Describe(inFeature).SpatialReference.Name != 102003:
      print('Projecting:', inFeature)
      outfc = os.path.join(self.scratch, cat + 'aoi')
      if not (arcpy.Exists(outfc)):
        arcpy.Project_management(inFeature, outfc, arcpy.SpatialReference(102003))
        return outfc
      else:
        return outfc        
    else:
      print('Spatial reference good')
      return inFeature

  def clipStuff(self, inFeature, cat):
    """
    Clips wetland to the area of interest.
    """
    outfc = inFeature
    if arcpy.Exists(outfc):
      print('Already have {} clipped with aoi'.format(cat))
      logging.info('Already have {} clipped with aoi'.format(cat))
    else:
      outfc = os.path.join(self.scratch, cat + 'clip')
      print('Clipping:', inFeature)
      logging.info("Clipping features")
      arcpy.Clip_analysis(inFeature, self.aoi, outfc)
    return outfc  
    

  def crossClass(self):
    """
    Joining large datasets is way too slow and may crash.  Iterating with a check for null will make sure all data is filled.
    """
    logging.info("Calculating habitat")
    if len(arcpy.ListFields(self.wetland,'CLASS'))>0:
      print('Already have CLASS field')
    else:
      print('Add CLASS habitat')
      arcpy.AddField_management(self.wetland, 'CLASS', "TEXT", 50)
    # Read data from file:
    dataDict = json.load(open(self.crossTbl))
    print(dataDict.keys())
    rows = arcpy.UpdateCursor(self.wetland, where_clause="CLASS='' OR CLASS=' '")
    for row in rows:
      for key,value in dataDict.items():
        if row.getValue('ATTRIBUTE') in value:
          row.setValue('CLASS', key)
          rows.updateRow(row)


  def prepEnergy(self, habtype = 'ATTRIBUTE'):
    """
    Returns habitat energy availability feature with a new field [avalNrgy] calculated from joining crosswalk table to habitat value and assigning energy.

    :param habtype: Habitat type field
    :type habtype: str
    :return: Available habitat feature
    :rtype: str
    """
    print(self.wetland)
    if len(arcpy.ListFields(self.wetland,'avalNrgy'))>0:
      print("Energy field exists")
    else:
      print("Adding energy field")
      arcpy.AddField_management(self.wetland, 'avalNrgy', "DOUBLE", 9, "", "", "AvailableEnergy")
    logging.info('Join kcal')
    if len(arcpy.ListFields(self.wetland,'kcal'))>0:
      print('Already have kcal field.  Deleting it')
      arcpy.DeleteField_management(self.wetland, ['kcal'])
    print('Join kcal')
    arcpy.JoinField_management(self.wetland, 'CLASS', self.kcalTbl, 'habitatType', ['kcal'])
    print('Calculate energy')
    logging.info("Calculate energy")
    if not len(arcpy.ListFields(self.wetland,'CalcAcre'))>0:
      arcpy.AddField_management(self.wetland, 'CalcAcre', "DOUBLE", 9, 2, "", "Acreage")
    arcpy.CalculateGeometryAttributes_management(self.wetland, "CalcAcre AREA", area_unit="ACRES")
    arcpy.CalculateField_management(self.wetland, 'avalNrgy', "!CalcAcre! * !kcal!", "PYTHON3")
    return "energy ready!"

  def dstOutout(self):
    """
    Runs energy difference between NAWCA stepdown objectives and available habitat.

    :return: Shapefile containing model results at the county level
    :rtype: str
    """
    return "outputFile"

  def bin(self, aggData, aggCol, bins):
    """
    Calculates proportional sum aggregate based on area within specified columns of a given dataset to features from another dataset.

    :param aggData: Dataset that contains information to be aggregated spatially
    :type aggData: str
    :param aggCol: Columns within aggData that need to have the sum aggregate function applied to them
    :type aggCol: str
    :param bins: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type bins: str
    :return: Spatial Sum aggregate of aggData within supplied bins
    :rtype:  str
    """
    return "binned file"