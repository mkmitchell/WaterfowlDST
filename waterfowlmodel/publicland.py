"""
Module Waterfowl
================
Defines Waterfowlmodel class which is initialized by supplying an area of interest shapfile, wetland shapefile, kilocalorie by habitat type table, and the table linking the wetland shapefile to the kcal table.
"""
import os, sys, getopt, datetime, logging, arcpy, json, csv
from arcpy import env
import waterfowlmodel.SpatialJoinLargestOverlap as overlap

class PublicLand:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi, land, name, binIt, scratch):
    """
    Creates a waterfowl model object.
    
    :param aoi: Area of interest shapefile
    :type aoi: str
    :param land: Public land location
    :type land: str
    :param name: NAme of public land
    :type name: str    
    :param binIt: Aggregation feature
    :type binIt: str    
    :param scratch: Scratch geodatabase location
    :type scratch: str
    """
    self.scratch = scratch
    self.aoi = aoi
    self.name = name
    self.land = self.projAlbers(self.clipStuff(land, name), name)
    self.binIt = binIt
    env.workspace = scratch

  def projAlbers(self, inFeature, cat):
    """
    Projects data to Albers

    :param inFeature: Feature to project to Albers
    :type inFeature: str
    :param cat: Feature category
    :type cat: str
    :return outfc: Location of projected feature
    :rtype outfc: str    
    """
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

    :param inFeature: Feature to clip to AOI
    :type inFeature: str
    :param cat: Feature category
    :type cat: str
    :return outfc: Location of clipped feature
    :rtype outfc: str
    """
    outfc = os.path.join(self.scratch, cat + 'clip')
    if arcpy.Exists(outfc):
      print('Already have {} clipped with aoi'.format(cat))
      logging.info('Already have {} clipped with aoi'.format(cat))
    else:
      print('Clipping:', inFeature)
      logging.info("Clipping features")
      arcpy.Clip_analysis(inFeature, self.aoi, outfc)
    return outfc  

  def bin(self, aggData, bins, cat):
    """
    Calculates proportional sum aggregate based on area within specified columns of a given dataset to features from another dataset.

    :param aggData: Dataset that contains information to be aggregated spatially
    :type aggData: str
    :param bins: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type bins: str
    :param cat: Spatial dataset used as the aggregation feature.  Data will be binned to the features within this dataset.
    :type cat: str    
    :return: Spatial Sum aggregate of aggData within supplied bins
    :rtype:  str
    """
    newbin = os.path.join(self.scratch, cat + 'bin')
    overlap.SpatialJoinLargestOverlap(bins,aggData,newbin,True, 'largest_overlap')
    return newbin
