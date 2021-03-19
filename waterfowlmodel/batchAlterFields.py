'''----------------------------------------------------------------------------------
 Tool Name:   Update field names in a feature class based on a table
 Source Name: batchAlterFields.py
 Version:     ArcPro
 Author:      Esri, Inc.
 Required Arguments:
              Target Features (Feature Layer)
              Dataframe table with at least the following colums: original field name, updated field name, field alias
 Optional Arguments:
              speciesrowfilter: which filters the rows based on list of row values.

 Description: Joins attributes from one feature class to another based on the spatial
              relationship between the two. The target features and the
              attributes from the join features are written to the output feature
              class. This tool presents a new spatial relationship, Largest Overlap,
              where a target feature is joined to the join feature with the largest
              area or length of overlap.
----------------------------------------------------------------------------------'''

def batchAlterFields(featureClass, scratch, fieldtable, speciesrowfilter=['ALL'], 
                     original_field_name_col='original_field_name', 
                     updated_field_name_col='field_name', 
                     updated_field_alias_col='field_alias'):

    """
    Aggregates species specific energy demand on a smaller scale to multple larger scale features.  Example: County to HUC12.

    :param featureClass: featureClass in which fields will be updated
    :type featureClass: str
    :param scratch: Scratch geodatabase location
    :type scratch: str  
    :param fieldtable: Table used to update the field names and aliases
    :type fieldtable: str
    :param speciesrowfilter: optional, a list of values used to filter the rows in the fieldtable
    :type speciesrowfilter: str
    :param original_field_name_col: Column/Attribute in fieldtable with the original field names 
    :type original_field_name_col: str
    :param updated_field_name_col: Column/Attribute in fieldtable with the updated field names
    :type updated_field_name_col: str
    :param updated_field_alias_col: Column/Attribute in fieldtable with the updated field aliases
    :type updated_field_alias_col: str
     """

    # Use Species filter to create a table of fields to update from the fieldtable
    if not speciesrowfilter:
        df = fieldtable.filter(items=[original_field_name_col, updated_field_name_col, updated_field_alias_col])            
    elif isinstance(speciesrowfilter, str):
        df = (fieldtable[fieldtable.species.isin([speciesrowfilter])]
                     .filter(items=[original_field_name_col, updated_field_name_col, updated_field_alias_col]))
    elif isinstance(speciesrowfilter, (list, tuple, set)):
        df = (fieldtable[fieldtable.species.isin(speciesrowfilter)]
                     .filter(items=[original_field_name_col, updated_field_name_col, updated_field_alias_col]))
        
    outputFields = [f.name for f in arcpy.ListFields(featureClass)]
    print(outputFields)
    
       for i, row in df.iterrows():
        if row[original_field_name_col] in outputFields:
            arcpy.AlterField_management(featureClass, 
                                        field=row[original_field_name_col], 
                                        new_field_name=row[updated_field_name_col],
                                        new_field_alias=row[updated_field_alias_col])
            
    newFieldList = [f.name for f in arcpy.ListFields(featureClass)]
    print("Fields changed to ...", newFieldList)