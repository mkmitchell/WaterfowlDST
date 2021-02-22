@ECHO OFF
python runModel.py -w "path to workspace where geodatabase and csvs are kept" -g Geodatabase_name.gdb -l NWILayer_name NWI_crossover.json -p PADUS_name -n NCED_name -k kcal_table.csv -d EnergyDemand_layer_name -e Extradataset1_layer_name Extradataset_crossover.csv -a AreaofInterest_name -b Bin_layer_nameu -u Unique Bin field -r Urban feature class -z debug 1 1 1 1 1 1 1
