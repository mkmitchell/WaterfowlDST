"""
Module Publicland
===================
This module defines the public land dataset and is used to organize and handle polygon features from NCED and PADUS.
"""
import os, sys, getopt, datetime, logging, arcpy, json, csv
from arcpy import env
import waterfowlmodel.SpatialJoinLargestOverlap as overlap

class PublicLand:
  """
  Creates a public lands object to store public land parameters.
    
  :param aoi: Polygon feature class denoting the model area of interest.
  :type aoi: str
  :param land: Polygon public land feature class.
  :type land: str
  :param name: Name of the public land feature class.
  :type name: str    
  :param binIt: Polygon feature class with the aggregation features. All data will be summarized within these polygons.
  :type binIt: str    
  :param scratch: Scratch geodatabase location.
  :type scratch: str
  """
  def __init__(self, aoi, land, name, binIt, scratch):
    self.scratch = scratch
    self.aoi = aoi
    self.name = name
    self.land = self.projAlbers(self.clipStuff(land, name), name)
    self.binIt = binIt
    env.workspace = scratch

  def projAlbers(self, inFeature, cat):
    """
    Projects spatial data from one coordinate system to USA Contiguous Albers Equal Area Conic (ESRI: 102003)

    :param inFeature: Input feature class or dataset.
    :type inFeature: str
    :param cat: Label, or category, for the projected output feature class or dataset.
    :type cat: str
    :return outfc: Path and name of projected output feature class.
    :rtype outfc: str    
    """
    if arcpy.Describe(inFeature).SpatialReference.Name != 102003:
      outfc = os.path.join(self.scratch, cat + 'aoi')
      if not (arcpy.Exists(outfc)):
        print('\tProjecting:', inFeature)
        arcpy.Project_management(inFeature, outfc, arcpy.SpatialReference(102003))
        return outfc
      else:
        return outfc        
    else:
      print('\tSpatial reference good')
      return inFeature

  def clipStuff(self, inFeature, cat):
    """
    Clipping Function.
    
    Clips a feature dataset to the area of interest.

    :param inFeature: Feature to clip to AOI
    :type inFeature: str
    :param cat: Feature category
    :type cat: str
    :return outfc: Location of clipped feature
    :rtype outfc: str
    """
    outfc = os.path.join(self.scratch, cat + 'clip')
    if arcpy.Exists(outfc):
      print('\tAlready have {} clipped with aoi'.format(cat))
      logging.info('Already have {} clipped with aoi'.format(cat))
    else:
      print('\tClipping:', inFeature)
      logging.info("Clipping features")
      arcpy.Clip_analysis(inFeature, self.aoi, outfc)
    return outfc  

  def bin(self, aggData, bins, cat):
    """
    Binning Function.
    
    Calculates a proportional sum aggregate based on an area within the specified columns of a given dataset to features from another dataset.

    :param aggData: Dataset that contains information to be spatially aggregated.
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
