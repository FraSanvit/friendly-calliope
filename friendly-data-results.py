### Modified from a part of  sector-coupled euro-calliope (https://github.com/calliope-project/sector-coupled-euro-calliope/blob/main/src/analyse/result_to_friendly.py)

### Copyright (c) 2018-2022 Bryn Pickering (ETH Zürich), Tim Tröndle (ETH Zürich / IASS Potsdam)
### Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
### The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR 
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR 
# OTHER DEALINGS IN THE SOFTWARE.


### Modifiers: Francesco Sanvito, Meijun Chen

import sys
import os
import glob
from pathlib import Path
import argparse

import pandas as pd

import calliope

from friendly_calliope.io import write_dpkg
from friendly_calliope import consolidate_calliope_output


# INPUTS

def main(path_to_results, path_to_friendly_results_folder):
    projection_year = "2050"
    scenario_dim_name = "scenario"

    storyline_config = {
        "names": (["people-powered", "government-directed", "market-driven"]),
        "primary_merge_storyline":{
            "p_p_deu_in_europe": "people-powered",
            "g_d_fra_in_europe": "government-directed",
            "non_eu_islands": "market-driven",
        },
        "primary_merge_country":{
            "p_p_deu_in_europe": "DEU",
            "g_d_fra_in_europe": "FRA",
            "non_eu_islands": "EU",
        },
        "viable_merged_combinations":([
            "p_p_deu_in_europe/government-directed",
            "p_p_deu_in_europe/market-driven",
            "g_d_fra_in_europe/market-driven",
            "g_d_fra_in_europe/people-powered",
            "non_eu_islands/government-directed",
            "non_eu_islands/people-powered"])
    }


    # {short scenario name : filename without file extension}
    scenario_dict = {'2050-compensation_abroad-dynamic_ntc-1h': '2050-compensation_abroad-dynamic_ntc-6h',
                    '2050-no_compensation_abroad-dynamic_ntc-1h':'2050-no_compensation_abroad-dynamic_ntc-6h',
                    '2050-neutral-dynamic_ntc-6h':'2050-neutral-dynamic_ntc-1h',
                    '2050-compensation_abroad-dynamic_ntc-1h-hcost': '2050-compensation_abroad-dynamic_ntc-6h-hcost',
                    '2050-no_compensation_abroad-dynamic_ntc-1h-hcost':'2050-no_compensation_abroad-dynamic_ntc-6h-hcost',
                    '2050-neutral-dynamic_ntc-1h-hcost':'2050-neutral-dynamic_ntc-6h-hcost'
    }

    scenario_path_list = glob.glob("{}/*.nc".format(path_to_results))
    scens_to_run_unsorted= []

    # Create a list of scenarios to run (scens_to_run) reading from the file path strings
    for path in scenario_path_list: scens_to_run_unsorted.append(Path(path).stem)
    if 'spore' in scens_to_run_unsorted[0]:
        scens_to_run = sorted(scens_to_run_unsorted, key=lambda x: int(x.split('_')[1]))
    else:
        scens_to_run = scens_to_run_unsorted
        
    country_names = pd.read_csv('auxiliary-data/regions.csv',sep=',',index_col=1)

    path_to_annual_demand = "{}/national/annual-demand-2050.csv".format(projection_year)
    path_to_industry_demand = "{}/annual_industry_energy_demand_2050.csv".format(projection_year)
    if 'spore' in scens_to_run_unsorted[0]:
        path_to_cost_optimal_file = path_to_results + "/spore_0.nc"
    else:
        path_to_cost_optimal_file = None
    path_to_scenario_files = "results"
    name = "calliope-scenarios-{}".format(projection_year)

    # resolution = "1" # H - model time resolution
    year = 2018 # model year

    final_ts_res = "hourly" # [annual|monthly|hourly]
    initial_keywords = ["scenarios", "PATHFNDR", "Nexus-e linkage"]

    description = "Calliope output PATHFNDR scenarios Dec-2022"
    # storyline_config = "" # might not be necessary for PATHFNDR
    merged_storylines = False
    # modifications Jared
    # path_to_output = f"{storyline}/friendly-results/{projection_year}/friendly_scenarios_{year}_{resolution}H_{projection_year}"

    # scens_to_run = ["2050-compensation_abroad-dynamic_ntc-1h"]
    # path_to_output = f"{storyline}/friendly-results/{projection_year}/{scens_to_run[0]}"

    # scen_name_set = {
    #                     'projection_year':0,
    #                     'co2_scenario':1,
    #                     'NTC_scenario':2,
    #                     'time_res':3,
    #                     'extra':4
    # }
    scen_name_set = {
                        'projection_year':0,
                        'co2_scenario':1,
                        'time_res':-1,
    }
    # francesco s sugggests: put projection_year first and time_res last, which are the most important things


    # DEFAULTS

    calliope.set_log_verbosity('INFO') #sets the level of verbosity of Calliope's operations

    for scenario in scens_to_run:
        print(scenario)
        scen_to_run = list([scenario])
        # the following doesn't work with file names like 'spore_1'
        projection_year = scenario.split("-")[scen_name_set['projection_year']]
        time_res = scenario.split("-")[scen_name_set['time_res']]
        resolution = scenario.split("-")[scen_name_set['time_res']].replace('h','')

        path_to_output = f"{path_to_friendly_results_folder}/{scenario}/data"
        if not os.path.exists(path_to_output):
            os.makedirs(path_to_output)

        data_dict = calliope_scenarios_to_friendly_file(
            scen_to_run, path_to_annual_demand, path_to_industry_demand, path_to_cost_optimal_file, scenario_dim_name,
            resolution, year, projection_year, final_ts_res, initial_keywords, name, description, storyline_config, merged_storylines, path_to_output,
            path_to_results
        )

ENERGY_PRODUCERS = {
    "waste_supply": "Waste",
    "biofuel_supply": "Biofuels",
    "hydro_reservoir": "Renewable electricity",
    "hydro_run_of_river": "Renewable electricity",
    "nuclear": "Nuclear electricity",
    "open_field_pv": "Renewable electricity",
    "roof_mounted_pv": "Renewable electricity",
    "wind_offshore": "Renewable electricity",
    "wind_onshore": "Renewable electricity",
    "methane_supply": "Natural gas",
    "diesel_supply": "Oil",
    "kerosene_supply": "Oil",
    "methanol_supply": "Oil",
    "coal_supply": "Coal",
    'syn_diesel_distribution_import': "Oil, carbon-neutral net imports",
    'syn_kerosene_distribution_import': "Oil, carbon-neutral net imports",
    'syn_methane_distribution_import': "Natural gas, carbon-neutral net imports",
    'syn_methanol_distribution_import': "Oil, carbon-neutral net imports",
}

SYNFUEL_EXPORT = {
    'syn_diesel_distribution_export': "Oil, carbon-neutral net imports",
    'syn_kerosene_distribution_export': "Oil, carbon-neutral net imports",
    'syn_methane_distribution_export': "Natural gas, carbon-neutral net imports",
    'syn_methanol_distribution_export': "Oil, carbon-neutral net imports"
}

HEAT_TECHS_BUILDING = ['biofuel_boiler', 'electric_heater', 'hp', 'methane_boiler']
HEAT_TECHS_DISTRICT = [
    'chp_biofuel_extraction', 'chp_methane_extraction', 'chp_wte_back_pressure', 'chp_hydrogen', 'chp_biomethane_extraction','chp_biogas',
    'chp_biofuel_extraction_ccs', 'chp_wte_back_pressure_ccs', 'chp_biomethane_extraction_ccs','chp_biogas_ccs',
]

### Generating the base data_dict

def calliope_scenarios_to_friendly_file(
    scens_to_run, path_to_annual_demand, path_to_industry_demand, path_to_cost_optimal_file, scenario_dim_name,
    resolution, year, projection_year, final_ts_res, initial_keywords, name, description, storyline_config, merged_storylines, path_to_output,
    path_to_results
):
    if final_ts_res == "annual":
        include_hourly = include_ts_in_file = False
    elif final_ts_res == "monthly": # check to produce monthly and hourly -> in cosolidate return_hourly always True
        include_hourly = False
        include_ts_in_file = True
    if final_ts_res == "hourly":
        include_hourly = include_ts_in_file = True

    """
    model_dict = {
        get_scenario(file, storyline_config, merged_storylines): calliope.read_netcdf(file)
        for file in path_to_scenario_files
    }
    """
    model_dict = {}
    for sc in scens_to_run: #scenario_dict.keys():
        try: 
            model_dict[sc]
        except:
            try:
                model_dict[sc] = calliope.read_netcdf('{}/{}.nc'.format(path_to_results,sc))
            except:
                pass
            pass
   
    if path_to_cost_optimal_file is not None:
        cost_opt_model = calliope.read_netcdf(path_to_cost_optimal_file)
    else:
        cost_opt_model = None

    data_dict = calliope_results_to_friendly(
        model_dict, cost_opt_model, path_to_annual_demand, path_to_industry_demand,
        scenario_dim_name, year, include_hourly, storyline_config, merged_storylines,
        scens_to_run
    )
    keywords = [
        initial_keywords, "calliope", "PATHFNDR", "Euro-Calliope",
        f"resolution={resolution}H",
        f"weather_year={year}",
        f"model_year={projection_year}"
    ]
    meta = {
        "name": name,
        "description": description,
        "keywords": keywords,
        "licenses": "CC-BY-4.0"
    }

    wrt_pckg(data_dict, path_to_output)
    """
    write_dpkg(
         data_dict, path_to_output, meta, include_timeseries_data=include_ts_in_file
    )
    """
    return data_dict


def calliope_results_to_friendly(
    model_dict, cost_opt_model, path_to_annual_demand, path_to_industry_demand,
    scenario_dim_name, year, include_ts, storyline_config, merged_storylines,
    scens_to_run
):

    data_dict = consolidate_calliope_output.combine_scenarios_to_one_dict(
        model_dict,
        cost_optimal_model=cost_opt_model,
        new_dimension_name=scenario_dim_name,
        return_hourly=include_ts,
        region_group="countries"
    )

    data_dict["primary_energy_supply"] = add_primary_energy_supply(data_dict)

    data_dict["final_consumption"] = add_final_energy_consumption(
        data_dict, year, path_to_industry_demand, scenario_dim_name,
        path_to_annual_demand, scens_to_run
    )

    data_dict["service_demand"] = add_service_demands(path_to_annual_demand, year, scens_to_run, scenario_dim_name, path_to_annual_demand)

    return data_dict

"""
def get_scenario(filepath, storyline_config, merged_storylines=False):
    curpath = os.path.abspath(os.curdir)
    fileabspath = os.path.abspath(filepath)
    split_filename = fileabspath.replace(curpath, "").split("/")
    if merged_storylines:
        return (
            storyline_config["primary_merge_country"][split_filename[5]],
            storyline_config["primary_merge_storyline"][split_filename[5]],
            split_filename[6]
        )
    else:
        return split_filename[1]
"""

def add_primary_energy_supply(data_dict):
    def _sum_over_techs(flow, tech_grouping):
        return (
            data_dict[flow]
            .dropna()
            .unstack("techs")
            .groupby(tech_grouping, axis=1).sum(min_count=1)
            .droplevel("carriers", axis=0)
            .rename_axis(columns="carriers")
            .stack()
            .dropna()
            .sum(level=data_dict[flow].index.names.difference(["techs"]))
        )

    flow_out_summed = _sum_over_techs("flow_out_sum", ENERGY_PRODUCERS)
    synfuel_exports = _sum_over_techs("flow_in_sum", SYNFUEL_EXPORT)
    flow_out_summed = flow_out_summed.sub(synfuel_exports, fill_value=0)

    flow_out_summed = flow_out_summed.append(
        data_dict["net_import_sum"]
        .rename_axis(index={"importing_region": "locs"})
        .rename({"electricity": "Net electricity import"}, level="carriers")
        .droplevel("exporting_region")
        .sum(level=flow_out_summed.index.names)
    )

    return flow_out_summed.sort_index()


def add_final_energy_consumption(
    data_dict, year, paths_to_industry_demand, scenario_dim_name,
    path_to_annual_demand, scens_to_run
):

    road_transport_consumption, heat_consumption, all_elec_consumption, countries, idx_order = (
        final_energy_consumption_from_data_dict(data_dict)
    )
    air_transport_consumption, shipping_transport_consumption, rail_transport_consumption, industry_total_elec_consumption = (
        final_energy_consumption_from_annual_demand(
            path_to_annual_demand, scens_to_run, idx_order, year, scenario_dim_name
        )
    )

    industry_subsector_consumption = pd.concat(
        final_energy_consumption_from_industry_subsectors(
            paths_to_industry_demand, year, scens_to_run, countries, scenario_dim_name, sc
        )
        for sc in scens_to_run
    )

    building_electricity_consumption = (
        all_elec_consumption
        .sub(rail_transport_consumption)
        .sub(industry_total_elec_consumption)
    )
    final_idx_order = [scenario_dim_name, "sector", "subsector", "carriers", "locs", "unit"]
    add_final_levels = add_sector_subsector(idx_order=final_idx_order)
    all_consumption = pd.concat([
        add_final_levels(road_transport_consumption, sector="Transport", subsector="Road"),
        add_final_levels(heat_consumption, sector="Buildings", subsector="Heat"),
        add_final_levels(air_transport_consumption, sector="Transport", subsector="Aviation"),
        add_final_levels(shipping_transport_consumption, sector="Transport", subsector="Shipping"),
        add_final_levels(rail_transport_consumption, sector="Transport", subsector="Rail"),
        add_final_levels(industry_subsector_consumption, sector="Industry"),
        add_final_levels(building_electricity_consumption, sector="Buildings", subsector="Appliances & cooling")
    ]).sort_index()

    return all_consumption


def final_energy_consumption_from_data_dict(data_dict):
    flow_in = data_dict["flow_in_sum"].dropna()
    flow_out = data_dict["flow_out_sum"].dropna()
    road_transport_techs = flow_out.xs("transport", level="carriers").unstack("techs").columns
    road_transport_consumption = (
        flow_in
        .unstack("techs")
        .loc[:, road_transport_techs]
        .sum(axis=1, min_count=1)
        .dropna()
    )

    heat_consumption_building = (
        flow_in[flow_in.index.get_level_values("techs").isin(HEAT_TECHS_BUILDING)]
        .unstack("techs")
        .sum(axis=1, min_count=1)
    )
    heat_consumption_district = (
        flow_out[
            flow_out.index.get_level_values("techs").isin(HEAT_TECHS_DISTRICT) &
            (flow_out.index.get_level_values("carriers") == "heat")
        ]
        .unstack("techs")
        .sum(axis=1, min_count=1)
    )
    heat_consumption = pd.concat([heat_consumption_building, heat_consumption_district])
    all_elec_consumption = flow_in.xs("demand_elec", level="techs")

    countries = flow_in.index.get_level_values("locs").unique()
    idx_order = [i for i in flow_out.index.names if i != "techs"]
    return (
        road_transport_consumption, heat_consumption, all_elec_consumption,
        countries, idx_order
    )


def final_energy_consumption_from_annual_demand(
    path_to_annual_demand, scens_to_run, idx_order, year, scenario_dim_name
):
    # if isinstance(paths_to_annual_demand, str):
    #     paths_to_annual_demand = [paths_to_annual_demand]
    air_transport_consumption = []
    shipping_transport_consumption = []
    rail_transport_consumption = []
    industry_total_elec_consumption = []

    # for path_to_annual_demand in paths_to_annual_demand:
    for sc in scens_to_run:
        annual_demand = read_tdf(path_to_annual_demand)
        # scenario = get_scenario(path_to_annual_demand, storyline_config, merged_storylines)
        scenario = sc

        air_transport_consumption.append(annual_demand_to_scenario_format(
            annual_demand
            .xs(("industry_demand", "air", year), level=("dataset", "cat_name", "year")),
            idx_order, scenario, scenario_dim_name
        ))
        shipping_transport_consumption.append(annual_demand_to_scenario_format(
            annual_demand
            .xs(("industry_demand", "marine", year), level=("dataset", "cat_name", "year")),
            idx_order, scenario, scenario_dim_name
        ))
        rail_transport_consumption.append(annual_demand_to_scenario_format(
            annual_demand
            .xs(("rail", year), level=("cat_name", "year"))
            .unstack("end_use")
            .loc[:, ["electricity"]]
            .stack()
            .sum(level=["locs", "unit", "end_use"], min_count=1),
            idx_order, scenario, scenario_dim_name
        ))
        industry_total_elec_consumption.append(annual_demand_to_scenario_format(
            annual_demand.xs(
                ("industry_demand", "industry", year),
                level=("dataset", "cat_name", "year")
            )
            .unstack("end_use")
            .loc[:, ["electricity"]]
            .stack(),
            idx_order, scenario, scenario_dim_name
        ))
        
        """
        prova = annual_demand.xs(
                ("industry_demand", "industry", year),
                level=("dataset", "cat_name", "year")
        ).xs(("electricity"),level=("end_use")
        ).assign(end_use="electricity"
        ).set_index("end_use", append=True)
        """

    return (pd.concat(i) for i in [
        air_transport_consumption, shipping_transport_consumption,
        rail_transport_consumption, industry_total_elec_consumption
    ])


def final_energy_consumption_from_industry_subsectors(                  # no recursive (it is already)
    path_to_industry_demand, year, scens_to_run, countries, scenario_dim_name, sc
):
    industry_demand = read_tdf(path_to_industry_demand)
    # scenario = get_scenario(path_to_industry_demand, storyline_config, merged_storylines)
    
    industry_subsector_consumption = (
        industry_demand
        .xs(year, level="year")
        .unstack("country_code")
        .groupby({get_alpha2(i): i for i in countries}, axis=1)
        .sum(min_count=1)
        .rename_axis(columns="locs", index={"carrier": "carriers"})
        .stack()
        .drop("space_heat", level="carriers")
    )
    industry_subsector_consumption = stack_all(
        industry_subsector_consumption
        .to_frame(sc)
        .rename_axis(columns=scenario_dim_name)
    )
    
    
    return industry_subsector_consumption.reorder_levels([scenario_dim_name, "subsector", "carriers", "locs", "unit"])


def annual_demand_to_scenario_format(annual_demand, idx_order, scenario, scenario_dim_name):
    units = annual_demand.index.get_level_values("unit").unique()
    dfs = []
    for scaled_unit in units:
        scale, unit = units.str.split(" ")[0]
        scale = float(scale)
        dfs.append(
            annual_demand
            .mul(scale)
            .rename({scaled_unit: unit}, level="unit")
            .rename_axis(index={"id": "locs", "end_use": "carriers"})
        )
    _df = pd.concat(dfs)

    _df = stack_all(
        _df
        .to_frame(scenario)
        .rename_axis(columns=scenario_dim_name)
    )

    return (
        _df
        .sort_index()
        .reorder_levels(idx_order)
    )


def stack_all(df):
    if isinstance(df.columns, pd.MultiIndex):
        df = df.stack(df.columns.names)
    else:
        df = df.stack()

    return df


def add_service_demands(paths_to_annual_demand, year, scens_to_run, scenario_dim_name, path_to_annual_demand):
    if isinstance(paths_to_annual_demand, str):
        paths_to_annual_demand = [paths_to_annual_demand]
    datasets = {
        "road_passenger": [],
        "road_freight": [],
        "heat_residential": [],
        "heat_commercial": [],
        "water_cooking_residential": [],
        "water_cooking_commercial": [],
    }
    idx_order = [scenario_dim_name, "locs", "unit"]
    final_idx_order = [scenario_dim_name, "sector", "subsector", "subsubsector", "locs", "unit"]
    add_final_levels = add_sector_subsector(idx_order=final_idx_order)
    annual_demand = read_tdf(path_to_annual_demand)

    for sc in scens_to_run:
        scenario = sc

        datasets["road_passenger"].append(annual_demand_to_scenario_format(
            annual_demand
            .xs(("transport_demand", "road", year), level=("dataset", "cat_name", "year"))
            .unstack("end_use")
            .loc[:, ["passenger_car", "motorcycle", "bus"]]
            .sum(axis=1, min_count=1)
            .dropna(),
            idx_order, scenario, scenario_dim_name
        ))
        datasets["road_freight"].append(annual_demand_to_scenario_format(
            annual_demand
            .xs(("road", year), level=("cat_name", "year"))
            .unstack(["dataset", "end_use"])
            .loc[:, pd.IndexSlice[["industry_demand", "transport_demand"], ["ldv", "hdv"]]]
            .sum(axis=1, min_count=1)
            .dropna(),
            idx_order, scenario, scenario_dim_name
        ))
        datasets["heat_residential"].append(annual_demand_to_scenario_format(
            annual_demand
            .xs(
                ("heat_demand", "household", year, "space_heat"),
                level=("dataset", "cat_name", "year", "end_use")
            ),
            idx_order, scenario, scenario_dim_name
        ))
        datasets["heat_commercial"].append(annual_demand_to_scenario_format(
            annual_demand
            .xs(
                ("heat_demand", "commercial", year, "space_heat"),
                level=("dataset", "cat_name", "year", "end_use")
            ),
            idx_order, scenario, scenario_dim_name
        ))
        datasets["water_cooking_residential"].append(annual_demand_to_scenario_format(
            annual_demand
            .xs(("heat_demand", "household", year), level=("dataset", "cat_name", "year"))
            .unstack("end_use")
            .loc[:, ["water_heat", "cooking"]]
            .sum(axis=1, min_count=1)
            .dropna(),
            idx_order, scenario, scenario_dim_name
        ))
        datasets["water_cooking_commercial"].append(annual_demand_to_scenario_format(
            annual_demand
            .xs(("heat_demand", "commercial", year), level=("dataset", "cat_name", "year"))
            .unstack("end_use")
            .loc[:, ["water_heat", "cooking"]]
            .sum(axis=1, min_count=1)
            .dropna(),
            idx_order, scenario, scenario_dim_name
        ))
    for dataset_name, dataset_vals in datasets.items():
        datasets[dataset_name] = pd.concat(dataset_vals)

    final_data_df = pd.concat([
        add_final_levels(
            datasets["road_passenger"],
            sector="Transport",
            subsector="Road",
            subsubsector="Passenger"
        ),
        add_final_levels(
            datasets["road_freight"],
            sector="Transport",
            subsector="Road",
            subsubsector="Freight"
        ),
        add_final_levels(
            datasets["heat_residential"],
            sector="Buildings",
            subsector="Space heat",
            subsubsector="Residential"
        ),
        add_final_levels(
            datasets["heat_commercial"],
            sector="Buildings",
            subsector="Space heat",
            subsubsector="Services"
        ),
        add_final_levels(
            datasets["water_cooking_residential"],
            sector="Buildings",
            subsector="Water heating and cooking",
            subsubsector="Residential"
        ),
        add_final_levels(
            datasets["water_cooking_commercial"],
            sector="Buildings",
            subsector="Water heating and cooking",
            subsubsector="Services"
        )
    ])
    return final_data_df


def add_sector_subsector(idx_order):
    def _add_sector_subsector(df, **kwargs):
        for dim_name, dim_val in kwargs.items():
            df = df.to_frame(dim_val).rename_axis(columns=dim_name).stack()
        return df.reorder_levels(idx_order).sort_index()
    return _add_sector_subsector


def read_tdf(path_to_file):
    df = pd.read_csv(path_to_file)
    rename_dict = {
        "id":"locs",
        "0":"value",
        "cat_name":"cat_name",
        "dataset":"dataset",
        "year":"year",
        "unit":"unit",
        "end_use":"end_use",
        "subsector": "subsector",
        "country_code": "country_code",
        "carrier":"carrier"
    }
    
    df = df.rename(columns={col: rename_dict[col] for col in df.columns})
    dict_ = {}
    for c in (df.columns):
        dict_new = {c: list(df[c])}
        dict_ = {**dict_, **dict_new}

    dict_df = pd.DataFrame(data=dict_)
    index_list = list(df.columns[:-1])
    dict_df = dict_df.set_index(index_list)

    indexes=dict_df.index
    series = list(df["value"])
    s = pd.Series(series, index=indexes)

    return s


def get_alpha2(country):
    country_dict={
    "ALB": "AL",
    "AUT": "AT",
    "BEL": "BE",
    "BIH": "BA",
    "BGR": "BG",
    "HRV": "HR",
    "CYP": "CY",
    "CZE": "CZ",
    "DNK": "DK",
    "EST": "EE",
    "FIN": "FI",
    "FRA": "FR",
    "DEU": "DE",
    "GRC": "GR",
    "HUN": "HU",
    "ISL": "IS",
    "IRL": "IE",
    "ITA": "IT",
    "LVA": "LV",
    "LIE": "LI",
    "LTU": "LT",
    "LUX": "LU",
    "MLT": "MT",
    "MNE": "ME",
    "NLD": "NL",
    "NOR": "NO",
    "POL": "PL",
    "PRT": "PT",
    "MKD": "MK",
    "ROU": "RO",
    "SRB": "RS",
    "SVK": "SK",
    "SVN": "SI",
    "ESP": "ES",
    "SWE": "SE",
    "CHE": "CH",
    "TUR": "TR",
    "UKR": "UA",
    "GBR": "GB",
    }
    alpha2_code=country_dict[country]

    return alpha2_code
    
def wrt_pckg (data_dict, path_to_output):
    for file, dataframe in data_dict.items():
        dataframe.to_csv("{}/{}.csv".format(path_to_output,file))
    return print("Data outputs are stored in {}/{}".format(path_to_output,file))    
"""
data_dict = calliope_scenarios_to_friendly_file(
    scens_to_run, path_to_annual_demand, path_to_industry_demand, path_to_cost_optimal_file, scenario_dim_name,
    resolution, year, projection_year, final_ts_res, initial_keywords, name, description, storyline_config, merged_storylines, path_to_output
)    
"""    



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path_to_results", type=str)
    parser.add_argument("path_to_friendly_results_folder", type=str)
    args = parser.parse_args()
    main(args.path_to_results, args.path_to_friendly_results_folder)