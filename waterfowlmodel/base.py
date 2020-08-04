"""
Module Waterfowl
================
Defines Waterfowlmodel class which is initialized by supplying an area of interest shapfile, wetland shapefile, kilocalorie by habitat type table, and the table linking the wetland shapefile to the kcal table.
"""
import os, sys, getopt, datetime, logging, arcpy, json, csv
from arcpy import env
import waterfowlmodel.SpatialJoinLargestOverlap as overlap
import pandas as pd

class Waterfowlmodel:
  """Class to store waterfowl model parameters."""
  def __init__(self, aoi, wetland, kcalTable, crosswalk, demand, binIt, binUnique, extra, scratch):
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
    :param binIt: Aggregation feature
    :type binIt: str
    :param binUnique: Unique field of aggregation feature
    :type binUnique: str        
    :param scratch: Scratch geodatabase location
    :type scratch: str
    """
    self.scratch = scratch
    self.aoi = self.projAlbers(aoi, 'aoi')
    self.binUnique = binUnique
    self.wetland = self.projAlbers(self.clipStuff(wetland, 'wetland'), 'wetland')
    self.kcalTbl = kcalTable
    self.crossTbl = crosswalk
    self.demand = self.projAlbers(self.clipStuff(demand, 'demand'), 'demand')
    self.binIt = self.projAlbers(self.clipStuff(binIt, 'bin'), 'bin')
    self.extra = self.processExtra(extra)
    self.mergedenergy = os.path.join(self.scratch, 'MergedEnergy')
    self.protectedMerge = os.path.join(self.scratch, 'MergedProtLands')
    self.protectedEnergy = os.path.join(self.scratch, 'protectedEnergy')
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
    
  def processExtra(self, extra):
    """
    Process all extra energy datasets

    :param extra: Feature to project to Albers
    :type extra: list
    :return cat: Dictionary of data location as keys and cross class table as value
    :rtype cat: dict
    """
    readyExtra = []
    a=0
    print(extra)
    for k in extra.keys():
      extra[k] = [self.projAlbers(self.clipStuff(extra[k][0], 'extra' + str(a)), 'extra' + str(a)),extra[k][1]]
      #readyExtra.append(self.projAlbers(self.clipStuff(extra[k][0], 'extra' + str(a)), 'extra' + str(a)))
      a+=1
    return extra

  def crossClass(self, inDataset, xTable, curclass='ATTRIBUTE'):
    """
    Joining large datasets is way too slow and may crash.  Iterating with a check for null will make sure all data is filled.

    :param inDataset: Feature to be updated with a new 'CLASS' field
    :type inDataset: str
    :param xTable: Location of csv or json file with two columns, from class and to class
    :type xTable: str
    :param curclass: Field that lists current class within inDataset
    :type curclass: str.
    """
    logging.info("Calculating habitat")
    print(inDataset)
    print(xTable)
    if len(arcpy.ListFields(inDataset,'CLASS'))>0:
      print('Already have CLASS field')
    else:
      print('Add CLASS habitat')
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
              row[1] = key
              cursor.updateRow(row)
        else:
          continue

  def joinFeatures(self):
    """
    Joins energy layers (Wetland with extra)

    :return: Merged feature location
    :rtype: str
    """    
    #Delete Wetland area from each extra dataset
    if arcpy.Exists(self.mergedenergy):
      print('Already joined habitat supply')
      return self.mergedenergy
    a=0
    erased = []
    erased.append(self.wetland)
    for i in self.extra.keys():
      #Erase(in_features, erase_features, out_feature_class, {cluster_tolerance})
      arcpy.Erase_analysis(self.extra[i][0], self.wetland, os.path.join(self.scratch, 'del' + str(i)))     
      erased.append(os.path.join(self.scratch, 'del' + str(i)))
      #Union(in_features, out_feature_class, {join_attributes}, {cluster_tolerance}, {gaps})
      arcpy.Merge_management(erased, self.mergedenergy)
    return self.mergedenergy

  def prepEnergy(self, habtype = 'ATTRIBUTE'):
    """
    Returns habitat energy availability feature with a new field [avalNrgy] calculated from joining crosswalk table to habitat value and assigning energy.

    :param habtype: Habitat type field
    :type habtype: str
    :return: Available habitat feature
    :rtype: str
    """
    if len(arcpy.ListFields(self.wetland,'avalNrgy'))>0:
      print("Energy field exists")
    else:
      print("Adding energy field")
      arcpy.AddField_management(self.wetland, 'avalNrgy', "DOUBLE", 9, "", "", "AvailableEnergy")
    print('Join kcal')
    logging.info('Join kcal')
    if len(arcpy.ListFields(self.wetland,'kcal'))>0:
      print('Already have kcal field.  Deleting it')
      arcpy.DeleteField_management(self.wetland, ['kcal'])
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

  def unionEnergy(self, supply, demand):
    """
    Merges all energy features into one feature.

    :return: Shapefile containing model results at the county level
    :rtype: str
    """
    arcpy.Union_analysis([supply, demand], os.path.join(self.scratch, "BinnedEnergyComparison"))

  def bin(self, aggData, bins, cat):
    """
    Aggregate sum based on maximum area overlap.

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

  def aggproportion(aggTo, aggData, IDField, aggFields, dissolveFields, scratch, cat,aggStat = 'SUM'):
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
    Aggregation_feature = aggTo
    Data_to_aggregate = aggData
    Fields_to_aggregate = aggFields
    FieldsToAgg = IDField + ' ' + IDField + ' VISIBLE NONE;'
    AggStats = ''
    for a in aggFields:
        FieldsToAgg = FieldsToAgg + a + ' ' + a + ' VISIBLE RATIO'
        AggStats = AggStats +  a + ' ' + aggStat + ';'
    WFSD_BCR = aggTo
    Dissolve_Field_s_ = [dissolveFields]
    # Local variables:
    outLayer = os.path.join(scratch, 'aggproptemp' + cat)
    outLayerI = os.path.join(scratch, 'aggUnion' + cat)
    aggToOut = os.path.join(scratch, 'aggTo' + cat)
    # Process: Make Feature Layer
    if arcpy.Exists(aggToOut):
      print('Already dissolved and aggregated everything')
      return aggToOut
    else:
      arcpy.MakeFeatureLayer_management(aggData, outLayer, "", "", FieldsToAgg)
      arcpy.Union_analysis(in_features=aggTo + ' #;' + outLayer, out_feature_class=outLayerI, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
    # Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
    # The following inputs are layers or table views: "aggUnionprotectedEnergy"
    #arcpy.Dissolve_management(in_features="aggUnionprotectedEnergy", out_feature_class="D:/OneDrive - Ducks Unlimited Incorporated/Documents/ArcGIS/Default.gdb/aggUnionprotectedEnergy_Diss", dissolve_field="HUC12", statistics_fields="avalNrgy SUM;CalcAcre SUM", multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
    arcpy.Dissolve_management(in_features=outLayerI, out_feature_class=aggToOut, dissolve_field=Dissolve_Field_s_, statistics_fields=AggStats, multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
    return aggToOut    

  def calcProtected(self):
    """
    Creates attribute for acres of habitat and acres of protected habitat
    """
    # Create attribute for total habitat acres.
    # clip merged energy with protected lands and calculate acres.  Create attribute for it.
    if not arcpy.Exists(self.protectedEnergy):
      arcpy.Clip_analysis(self.mergedenergy, self.protectedMerge, self.protectedEnergy)
      arcpy.CalculateField_management(in_table=self.protectedEnergy, field="CalcAcre", expression="!shape.area@acres!", expression_type="PYTHON_9.3", code_block="")
      arcpy.CalculateField_management(in_table=self.protectedEnergy, field="avalNrgy", expression="!CalcAcre!* !kcal!", expression_type="PYTHON_9.3", code_block="")

  def prepProtected(self, nced, padus):
    """
    Prepares protected lands by merging nced and padus by deleting NCED from PAD and running a union.
    """
    #Erase(in_features, erase_features, out_feature_class, {cluster_tolerance})
    if not arcpy.Exists(os.path.join(self.scratch, 'delncedfrompad')):
      arcpy.Erase_analysis(padus, nced, os.path.join(self.scratch, 'delncedfrompad'))
    #Union(in_features, out_feature_class, {join_attributes}, {cluster_tolerance}, {gaps})
    if not arcpy.Exists(self.protectedMerge):
      arcpy.Merge_management([nced, os.path.join(self.scratch, 'delncedfrompad')], self.protectedMerge)

  def pctHabitatType(self):
    """
    Calculates proportion of habitat type by bin unit.
    """
    print(os.path.join(self.scratch, "HabitatInAOI"))
    arcpy.RepairGeometry_management(self.mergedenergy)
    arcpy.RepairGeometry_management(self.aoi)
    if not arcpy.Exists(os.path.join(self.scratch, "HabitatInAOI")):
      arcpy.Union_analysis([self.mergedenergy, self.aoi], os.path.join(self.scratch, "HabitatInAOI"))
    if not arcpy.Exists(os.path.join(os.path.dirname(self.scratch),'tbl.csv')):  
      arcpy.TableToTable_conversion(in_rows=os.path.join(self.scratch, "HabitatInAOI"), out_path=os.path.dirname(self.scratch), out_name="tbl.csv", where_clause="", config_keyword="")
    print('Converting to pandas')
    df = pd.read_csv(os.path.join(os.path.dirname(self.scratch),'tbl.csv'))
    df1 = df.groupby([binUnique]).CalcAcre.sum()
    df['pct'] = df['CalcAcre']/pd.merge(df, df1, on=[binUnique,binUnique],how='left')['CalcAcre_y']*100
    outdf = df.pivot(index=binUnique, columns='CLASS', values='CalcAcre')
    outnp = np.array(np.rec.fromrecords(outdf.values))
    names = outdf.dtypes.index.tolist()
    outnp.dtype.names = tuple(names)
    print('Back to ESRI')
    arcpy.da.NumPyArrayToTable(outnp, os.path.join(self.scratch, 'HabitatPct'))
    return os.path.join(self.scratch, 'HabitatPct')