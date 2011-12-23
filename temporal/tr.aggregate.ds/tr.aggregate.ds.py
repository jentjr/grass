#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:	tr.aggregate.ds
# AUTHOR(S):	Soeren Gebbert
#
# PURPOSE:	Aggregated data of an existing space time raster dataset using the temporal topology of a second space time dataset
# COPYRIGHT:	(C) 2011 by the GRASS Development Team
#
#		This program is free software under the GNU General Public
#		License (version 2). Read the file COPYING that comes with GRASS
#		for details.
#
#############################################################################

#%module
#% description: Aggregated data of an existing space time raster dataset using the temporal topology of a second space time dataset
#% keywords: spacetime raster dataset
#% keywords: raster
#% keywords: aggregation
#%end

#%option
#% key: input
#% type: string
#% description: Name of a space time raster dataset
#% required: yes
#% multiple: no
#%end

#%option
#% key: sample
#% type: string
#% description: The time intervals from this space time dataset (raster, vector or raster3d) are used for aggregation computation. 
#% required: yes
#% multiple: no
#%end

#%option
#% key: type
#% type: string
#% description: Type of the aggregation space time dataset, default is strds
#% required: no                                                 
#% options: strds, str3ds, stvds
#% answer: strds                                                
#%end                                                           

#%option
#% key: output
#% type: string
#% description: Name of the output space time raster dataset
#% required: yes
#% multiple: no
#%end

#%option
#% key: method
#% type: string
#% description: Aggregate operation to be peformed on the raster maps
#% required: yes
#% multiple: no
#% options: average,count,median,mode,minimum,min_raster,maximum,max_raster,stddev,range,sum,variance,diversity,slope,offset,detcoeff,quart1,quart3,perc90,quantile,skewness,kurtosis
#% answer: average
#%end

#%option
#% key: sampling
#% type: string
#% description: The method to be used for sampling the input dataset
#% required: no
#% multiple: yes
#% options: start,during,overlap,contain,equal
#% answer: start
#%end

#%option
#% key: base
#% type: string
#% description: Base name of the new created raster maps
#% required: yes
#% multiple: no
#%end

#%flag
#% key: n
#% description: Register Null maps
#%end

import grass.script as grass
import grass.temporal as tgis

############################################################################

def main():

    # Get the options
    input = options["input"]
    output = options["output"]
    sampler = options["sample"]
    base = options["base"]
    register_null = flags["n"]
    method = options["method"]
    type = options["type"]
    sampling = options["sampling"]

    # Make sure the temporal database exists
    tgis.create_temporal_database()
    # We need a database interface
    dbif = tgis.sql_database_interface()
    dbif.connect()
   
    mapset =  grass.gisenv()["MAPSET"]

    if input.find("@") >= 0:
        id = input
    else:
        id = input + "@" + mapset

    sp = tgis.space_time_raster_dataset(id)
    
    if sp.is_in_db() == False:
        dbif.close()
        grass.fatal(_("Dataset <%s> not found in temporal database") % (id))

    sp.select(dbif)

    if sampler.find("@") >= 0:
        sampler_id = sampler
    else:
        sampler_id = sampler + "@" + mapset

    sampler_sp = tgis.dataset_factory(type, sampler_id)
    
    if sampler_sp.is_in_db() == False:
        dbif.close()
        grass.fatal(_("Dataset <%s> not found in temporal database") % (id))

    sampler_sp.select(dbif)

    if sampler_sp.get_temporal_type() != sp.get_temporal_type():
        dbif.close()
        grass.fatal(_("Input and aggregation dataset must have the same temporal type"))

    # Check if intervals are present
    if sampler_sp.get_temporal_type() == "absolute":
        map_time = sampler_sp.absolute_time.get_map_time()
    else:
        map_time = sampler_sp.relative_time.get_map_time()
    
    if map_time != "interval":
        dbif.close()
        grass.fatal(_("All registered maps of the aggregation dataset must have time intervals"))

    if output.find("@") >= 0:
        out_id = output
    else:
        out_id = output + "@" + mapset

    # The new space time raster dataset
    new_sp = tgis.space_time_raster_dataset(out_id)
    if new_sp.is_in_db(dbif):
        if grass.overwrite() == True:
            new_sp.delete(dbif)
            new_sp = tgis.space_time_raster_dataset(out_id)
        else:
            dbif.close()
            grass.fatal(_("Space time raster dataset <%s> is already in database, use overwrite flag to overwrite") % out_id)

    temporal_type, semantic_type, title, description = sp.get_initial_values()
    new_sp.set_initial_values(temporal_type, semantic_type, title, description)
    new_sp.insert(dbif)

    rows = sampler_sp.get_registered_maps("id,start_time,end_time", None, "start_time", dbif)

    if not rows:
            dbif.close()
            grass.fatal(_("Aggregation dataset <%s> is empty") % id)

    count = 0
    for row in rows:
        count += 1
        start = row["start_time"]
        end = row["end_time"]

        input_map_names = tgis.collect_map_names(sp, dbif, start, end, sampling)

        if input_map_names:
            tgis.aggregate_raster_maps(new_sp, mapset, input_map_names, base, start, end, count, method, register_null, dbif)
        

    # Update the spatio-temporal extent and the raster metadata table entries
    new_sp.update_from_registered_maps(dbif)
        
    dbif.close()

if __name__ == "__main__":
    options, flags = grass.parser()
    main()

