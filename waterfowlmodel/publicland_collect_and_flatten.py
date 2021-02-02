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

  def getNCED(self, itemID = 'e5117faf3ecc472c9b5d3392711a7ccf', exportFolder, cat):
    """
    Downloads NCED as a zipped gdb from the Ducks Unlimited's internal GIS portal,
    and unzips it. Modified from https://community.esri.com/t5/arcgis-api-for-python-questions/can-someone-help-me-fix-this-automated-download-script/m-p/839999

    :param itemID: NCED's item ID number in DU's GIS portal.
    :type itemID: str
    :param cat: Feature category
    :type cat: str
    :exportFolder: the folder in which the geodatabase will be downloaded.
    :type exportFolder: file location
    """ 

    # get NCED from the DU portal
    item = gis.content.get(itemID)
    # Export hosted feature service to FGD, and downlaod
    export_name = "export_" + item.title
    result_item = item.export(export_name, 'File Geodatabase', wait=True)
    print("Exported: {}".format(result_item))
    download_result = result_item.download(exportFolder)
    print("Saved to: {}".format(download_result))
    result_item.delete()
    print("Deleted result")

    # Extract zip file
    with ZipFile(download_result, 'r') as zipObj:
      # Extract all the contents of zip file in current directory
      zipObj.extractall(exportFolder)
      print("Unzipped {0}".format(download_result))

    # return polygon feature
    
  
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