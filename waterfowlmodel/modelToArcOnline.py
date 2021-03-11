'''----------------------------------------------------------------------------------
 Tool Name:   Create Public-Facing Feature Class for ABDU
 Source Name: modelToArcOnline.py
 Version:     ArcPro
 Author:      Esri, Inc.
 Required Arguments:
              Target Features (Feature Layer)
              Join Features (Feature Layer)
              Output Feature Class (Feature Class)
 Optional Arguments:
              Keep All (True|False)
              Spatial Relationship (String)

 Description: Joins attributes from one feature class to another based on the spatial
              relationship between the two. The target features and the
              attributes from the join features are written to the output feature
              class. This tool presents a new spatial relationship, Largest Overlap,
              where a target feature is joined to the join feature with the largest
              area or length of overlap.
----------------------------------------------------------------------------------'''

# Import system modules
import arcpy
import os
from arcgis import GIS
import pandas as pd

arcpy.env.overwriteOutput = True

def createPublicLayer(fieldTable, folder):

    # Create Geodatabase names ModelOutputs_WMS.gdb
    gdb = os.path.join(folder, 'ModelOutputs_WMS.gdb')
    if not arcpy.Exists(gdb):
        arcpy.CreateFileGDB_management(folder, 'ModelOutputs_WMS.gdb')

    arcpy.env.workspace = gdb

    # Create Feature Class
    spatial_ref = arcpy.SpatialReference('WGS 1984 Web Mercator (auxiliary sphere)')
    if not arcpy.Exists(os.path.join(folder, gdb, 'abdu_dst')):
        arcpy.CreateFeatureclass_management(gdb, 'abdu_dst', "POLYGON", "","DISABLED", "DISABLED", spatial_ref)

    # import csv
    if fieldTable.endswith('.csv'):
        df = pd.read_csv(csv_fields, encoding='unicode_escape')

    df_short = df[['field_name', 'field_type', 'field_alias']].values.tolist()

    arcpy.management.AddFields('abdu_dst', df_short)
    
# Main function
def modelToArcOnline(fieldTable, modelOutput, out_fc):

    # field Table to dataframe
    if fieldTable.endswith('.csv'):
        df = pd.read_csv(csv_fields, encoding='unicode_escape')

    # simplify
    arcpy.cartography.SimplifyPolygon(os.path.join(gdb, modelOutput), 
                                  output_simplified, 
                                  "BEND_SIMPLIFY", "1000 Meters", "0 SquareMeters", "RESOLVE_ERRORS", "KEEP_COLLAPSED_POINTS", None)

    # re-project to WMS
    out_CS = arcpy.SpatialReference('WGS 1984 Web Mercator (auxiliary sphere)')
    out_wms = os.path.join(gdb,'{}_wms'.format(output_simplified))
    arcpy.Project_management(output_simplified, out_wms, out_CS)

    # standardize attributes against field table
    sdf = pd.DataFrame.spatial.from_featureclass(out_wms)

    # merge with feature service on huc12

    # final qaqc

    # complete replace


# Run the script
if __name__ == '__main__':
    # Get Parameters
    field_table = arcpy.GetParameterAsText(0)
    out_fc = arcpy.GetParameterAsText(2)

    SpatialJoinLargestOverlap(field_table, out_fc)
    print("finished")