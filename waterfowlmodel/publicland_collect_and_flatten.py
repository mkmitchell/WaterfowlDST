  # two functions to add to the public lands part?
  # python 3 / Jes / 2021, etc.

  import os, arcpy

"""  authentication information under 'User authentication with OAuth 2.0' here: 
  https://developers.arcgis.com/python/guide/working-with-different-authentication-schemes/"""

# this is causing problems
gis = GIS("https://gisweb.ducks.org/portal/home/", client_id='o9FHjvcWBUtxp00v')
print("Successfully logged in as: " + gis.properties.user.username)

# if signed into portal on arcpro, can also use this:
#gis=GIS("pro")
#print("Successfully logged in as: " + gis.properties.user.username)

  def getNCED(self, itemID = 'e5117faf3ecc472c9b5d3392711a7ccf'):
      item = gis.content.get(itemID)
      result=extract_data(item.layers, output_name='NCED', data_format='FILEGEODATABASE')

      return result
  
  def flattenLayer(self, inFeature, scratchgdb, cat):
    """
    Removes overlaps in protected lands layer.

    :param inFeature: Feature to flatten
    :type inFeature: str
    :param cat: Feature category
    :type cat: str
    :scratchgdb: scratch geodatabase, for intermediate steps
    :type scratchgdb: geodatabase/workspace
    :return outfc: Location of flattened feature
    :rtype outfc: str    
    """ 

    # set intermediate variables
    inFile= os.path.basename(inFeature)
    (inName, ext) = os.path.splitext(inFile)
    outUnion = os.path.join(scratchgdb, "{}_union".format(inName))
    outDissolve = os.path.join(scratchgdb, "{}_diss".format(outUnion))
    outfc

    # union all features, this retains attributes
    arcpy.analysis.Union(inFeature, outUnion, "ALL", None, "GAPS")

    # dissolve all features
    arcpy.management.Dissolve(outUnion, outDissolve, None, None, "MULTI_PART", "DISSOLVE_LINES")

    # multipart to singlepart
    arcpy.management.MultipartToSinglepart(outDissolve, outfc)

    return outfc