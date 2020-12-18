"""
addLabel
===============
addLabel adds a label field to the model output.
"""
# import modules
import os, arcpy
from arcgis.gis import GIS
  
def AddHUCNames(outputfc, output_hucID_field_name = 'HUC12', hucFC, hucID_field_name = 'huc12', hucName_field_name='name'):

    """
    Adds a label field to the model output so that the sub-watersheds can be labelled by name. 

    :param outputfc: The path to the model output feature class
    :type outputfc: str
    :param output_hucID_field_name: The default field name for the HUC12 watershed ID in the model output. Defaults to 'HUC12'
    :type output_hucID_field_name: str
    :param hucFC: The path to the feature class or shapefile containing the watershed IDs and names.
    :type hucFC: str
    :param hucID_field_name: The fieldname in hucFC for the watershed ID numbers. Defaults to 'huc12'.
    :type hucID_field_name: str
    :param hucName_field_name: The fieldname in hucFC for the watershed names. Defaults to 'name'.
    :type hucName_field_name: str

    """

    # create dictionary of huc IDs, assumes the huc 12 layer is shapefile or a feature class in a geodatabase.
    sdf = pd.DataFrame.spatial.from_featureclass(hucFC)
    sdfDict = dict(zip(sdf[hucID_field_name], sdf[hucName_field_name]))

    # Add the Map Label Field to the output
    fds = [f.name for f in arcpy.ListFields(outputfc)]
    if 'label' not in fds:
        arcpy.AddField_management(outputfc, "label", "TEXT", "", "", "", "Map Label")

    # Add HUC Name
    with arcpy.da.UpdateCursor(outputfc, [output_hucID_field_name, 'label']) as cursor:
        for row in cursor:
            if not row[1] and row[0] in sdfDict:
                row[1] = sdfDict[row[0]]
                print(row[1])
            elif not row[1] and row[0] not in sdfDict:
                row[1] = row[0]
            cursor.updateRow(row)