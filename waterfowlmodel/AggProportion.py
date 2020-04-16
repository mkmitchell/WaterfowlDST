"""
Module Aggregate by proportion
================
Aggregates attributes from one set of features to another based on proportion overlap.
"""
import arcpy, os

class AggregateProportion:
  """Class to aggregate features by intersection and proportion."""

  def aggproportion(aggTo, aggData, IDField, aggFields, dissolveFields, scratch, cat,aggStat = 'SUM'):
    # Script arguments
    Aggregation_feature = aggTo
    Data_to_aggregate = aggData
    Fields_to_aggregate = aggFields
    FieldsToAgg = IDField + ' ' + IDField + ' VISIBLE NONE;'
    AggStats = ''
    for a in aggFields:
        FieldsToAgg = FieldsToAgg + a + ' ' + a + ' VISIBLE RATIO'
        AggStats = AggStats +  a + ' ' + aggStat
        #Fields_to_aggregate = "FID FID VISIBLE NONE;Shape Shape VISIBLE NONE;SQMI SQMI VISIBLE NONE;ACRE ACRE VISIBLE NONE;ICP ICP VISIBLE NONE;LCP LCP VISIBLE NONE;BCR BCR VISIBLE NONE;JV JV VISIBLE NONE;species species VISIBLE NONE;fips fips VISIBLE NONE;CODE CODE VISIBLE NONE;LTADUD LTADUD VISIBLE RATIO;X80DUD X80DUD VISIBLE RATIO;LTAPopObj LTAPopObj VISIBLE RATIO;X80PopObj X80PopObj VISIBLE RATIO;LTADemand LTADemand VISIBLE RATIO;X80Demand X80Demand VISIBLE RATIO;REGION REGION VISIBLE NONE;Shape_Leng Shape_Leng VISIBLE NONE;Shape_Area Shape_Area VISIBLE NONE" # provide a default value if unspecified
    WFSD_BCR = aggTo
    Dissolve_Field_s_ = [dissolveFields]
    # Local variables:
    outLayer = os.path.join(scratch, 'aggproptemp' + cat)
    outLayerI = os.path.join(scratch, 'aggUnion' + cat)
    aggToOut = os.path.join(scratch, 'aggTo' + cat)
    # Process: Make Feature Layer
    print('Make Feature Layer')
    arcpy.MakeFeatureLayer_management(aggData, outLayer, "", "", FieldsToAgg)
    print('Union')
    arcpy.Union_analysis(in_features=aggTo + ' #;' + outLayer, out_feature_class=outLayerI, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
    print('Dissolve')
    #arcpy.Dissolve_management(outLayerI, aggTo, Dissolve_Field_s_, AggStats, "MULTI_PART", "DISSOLVE_LINES")
    arcpy.Dissolve_management(in_features=outLayerI, out_feature_class=aggToOut, dissolve_field=Dissolve_Field_s_, statistics_fields=AggStats, multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")
    print("Acres ready!")
    return aggToOut
