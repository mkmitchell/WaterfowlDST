@ECHO OFF
::[Supply, Demand, species proportion, protected lands, habitat proportion, weighted mean, data check, zip it]
::python runModel.py -w "path to workspace" -g Geodatabase_name.gdb -l NWILayer_name NWI_crossover.json 
::-p PADUS_name -n NCED_name -k kcal_table.csv -d EnergyDemand_layer_name -e Extradataset1_layer_name Extradataset_crossover.csv 
::-a AreaofInterest_name -b Bin_layer_name -u Unique_Bin_field Bin_name -r Urban_feature_class -f Field_Table -z debug 1 1 1 1 1 1 1 1
python runModel.py -w "C:\Workspace\TestDB\TestDB" -g test.gdb -l NWI NWICrossClass.json -p pad -n nced -k kcal.csv -d demand -a SmallTest -b huc -u huc12 name -r urban -f ModelOutputFieldDictionary.csv -z 1 1 1 1 1 1 1 1