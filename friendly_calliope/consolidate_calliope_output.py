import argparse

import pandas as pd
import numpy as np
import xarray as xr
import copy

import calliope
from calliope.core.util.dataset import split_loc_techs

from friendly_calliope.io import get_models_from_file, write_dpkg

ZERO_THRESHOLD = 5e-12  # capacities lower than this will be considered as effectively zero, default: 5e-6
COST_NAME_MAPPING = {
    'cost_energy_cap': "cost_per_nameplate_capacity",
    'cost_om_prod': "cost_per_flow_out",
    'cost_om_annual_investment_fraction': "annual_cost_per_unit_invested",
    'cost_storage_cap': "cost_per_storage_capacity",
    'cost_om_annual': "annual_cost_per_nameplate_capacity",
    'cost_depreciation_rate': "depreciation_rate",
    'cost_om_con': "cost_per_flow_in",
    'cost': 'total_system_cost',
    'cost_investment': 'total_investment_cost',
    'cost_var': 'total_operation_cost',
}

EMISSIONS_NAME_MAPPING = {
    'cost_energy_cap': "emissions_per_nameplate_capacity",
    'cost_om_prod': "emissions_per_flow_out",
    'cost_om_annual_investment_fraction': "annual_emissions_per_unit_invested",
    'cost_storage_cap': "emissions_per_storage_capacity",
    'cost_om_annual': "annual_emissions_per_nameplate_capacity",
    'cost_depreciation_rate': "depreciation_rate",
    'cost_om_con': "emissions_per_flow_in",
    'cost': 'total_system_emissions',
    'cost_investment': 'total_investment_emissions',
    'cost_var': 'total_operation_emissions',
}

OLD_TECH_NAMES = {
    'battery': "Battery storage",
    'biofuel_boiler': "Biomass boiler",
    'biofuel_supply': "Biofuel",
    'biogas_supply': "Biogas",
    'biofuel_to_diesel': "Biofuel to vehicle fuel (we only consider diesel) converter",
    'biofuel_to_liquids': "Biofuel to liquid fuels converter",
    'biofuel_to_methane': "Biofuel to Methane converter",
    'biofuel_to_methanol': "Biofuel to Methanol converter",
    'ccgt': "Combined cycle gas turbine",
    'chp_biofuel_extraction': "Centralised biofuel steam extraction turbine combined heat and power",
    'chp_wte_back_pressure': "Centralised waste stream back pressure combined heat and power",
    'dac': "Direct air CO2 capture",
    'electric_heater': "Electrical heater",
    'electric_hob': "Electric cooking element",
    'electrolysis': "Hydrogen by electrolysis",
    'gas_hob': "Electric cooking element",
    'heat_storage_big': "District-scale heat storage vessels",
    'heat_storage_small': "Building-scale heat storage vessels",
    'heavy_transport_ev': "Electric heavy vehicles",
    'heavy_transport_ice': "Internal combustion engine heavy vehicles",
    'hp': "Heat pump",
    'hydro_reservoir': "Hydro electricity with a reservoir.",
    'hydro_run_of_river': "Run of river hydro electricity",
    'hydrogen_storage': "Hydrogen power storage",
    'hydrogen_to_liquids': "Hydrogen to liquid fuels converter",
    'hydrogen_to_methane': "Hydrogen to Methane converter",
    'hydrogen_to_methanol': "Hydrogen to Methanol converter",
    'light_transport_ev': "Electric light vehicles",
    'light_transport_ice': "Internal combustion engine light vehicles",
    'methane_boiler': "Gas boiler",
    'methane_storage': "Underground methane storage",
    'nuclear': "Nuclear power",
    'open_field_pv': "Open field PV",
    'pumped_hydro': "Pumped hydro power storage",
    'roof_mounted_pv': "Roof mounted PV",
    'syn_diesel_converter': "Dummy tech to allow synthetic diesel to meet demand",
    'syn_diesel_distribution_import': "syn_diesel_distribution_import",
    'syn_kerosene_converter': "Dummy tech to allow synthetic kerosene to meet demand",
    'syn_kerosene_distribution_import': "syn_kerosene_distribution_import",
    'syn_methane_converter': "Dummy tech to allow synthetic methane to meet demand",
    'syn_methane_distribution_import': "syn_methane_distribution_import",
    'syn_methanol_converter': "Dummy tech to allow synthetic methanol to meet demand",
    'syn_methanol_distribution_import': "syn_methanol_distribution_import",
    'waste_supply': "Municipal waste supply",
    'wind_offshore': "Offshore wind",
    'wind_onshore': "Onshore wind"
}

NEW_TECH_NAMES = {
    "heat_storage_big": "District-scale heat storage vessels",
    "heat_storage_small": "Building-scale heat storage vessels",
    "wind_onshore": "Onshore wind",
    "chp_wte_back_pressure_ccs": "Centralised waste stream back pressure combined heat and power with CCS",
    "ccgt_ccs": "Combined cycle gas turbine with CCS",
    'chp_biofuel_extraction_ccs': "Centralised biofuel steam extraction turbine combined heat and power with CCS",
    "chp_hydrogen": "Centralised hydrogen-fuelled combined heat and power plant",
    "chp_methane_extraction": "Centralised hydrogen steam extraction turbine combined heat and power",
    "biogas_to_electricity_supply": "Anaerobic digestion plant plus cnversion into electricity",
    "chp_biomethane_extraction": "Centralised biomethane steam extraction turbine combined heat and power",
    "chp_biomethane_extraction_ccs": "Centralised biomethane steam extraction turbine combined heat and power with CCS",
    "biomethane_converter": "Dummy tech to allow biomethane to meet demand",
    "biogas_upgrading": "Conversion of biogas into biomethane",
    
}

loc_newtech_dict = {
    "heat_storage_big": "heat",
    "heat_storage_small": "heat",
    "wind_onshore": "electricity"
}

def combine_scenarios_to_one_dict(
    model_dict, cost_optimal_model=None, new_dimension_name="scenario", return_hourly=True,
    **kwargs
):
    """
    Take in a dictionary of Calliope models and create a dictionary of processed data ready to share with the world
    """
    all_data_dict = {}
    if cost_optimal_model is None:
        cost_optimal_model = list(model_dict.values())[0]
    if isinstance(new_dimension_name, str):
        new_dimension_name = [new_dimension_name]
     
    # cost_optimal_model = list(model_dict.values())[0]
    #print("model.inputs type:  ",type(cost_optimal_model.inputs))
    #print("model.inputs.timesteps:  ",cost_optimal_model.inputs.timesteps)
    #print("len of model.inputs.timesteps:  ",len(list(cost_optimal_model.inputs.timesteps)))
   # print("len of model.inputs.coords['timesteps']:  ",len(cost_optimal_model.inputs.coords['timesteps']))
    
    names = pd.Series(list(cost_optimal_model._model_data.techs_conversion_plus.values) + list(cost_optimal_model._model_data.techs_conversion.values))
    
    # loc_tech_carrier = pd.Series(model._model_data.loc_tech_carriers_prod.values)
    # timestep = cost_optimal_model.inputs.timestep_resolution.mean().item()
    timestep = round(8760/len(list(cost_optimal_model.inputs.timesteps))) # to be reactivated
    # timestep =int(1)
    
    """
    names = cost_optimal_model._model_data.techs_conversion_plus.values
    names = cost_optimal_model.inputs.names.to_series()
    print(cost_optimal_model.inputs)
    kwargs["timestep_resolution"] = cost_optimal_model.inputs.timestep_resolution.mean().item()
    assert cost_optimal_model.inputs.timestep_resolution.std().item() == 0, "Can only work with a consistent timestep resolution"
    """
    all_data_dict.update(get_input_costs(cost_optimal_model.inputs, **kwargs))
    energy_caps = pd.concat(
        [get_energy_caps(model, **kwargs) for model in model_dict.values()],
        keys=model_dict.keys(), names=new_dimension_name,
    )
    valid_loc_techs = get_valid_loc_techs(energy_caps)
    
    valid_tech_list = energy_caps.index.get_level_values("techs")
    demand_list = tech_list_subset(energy_caps,"demand")
    distribution_export_list = tech_list_subset(energy_caps,"distribution_export")
    exception_tech_list = ["demand_co2"]
    
    tech_list_to_remove = list(set(demand_list+distribution_export_list)-set(exception_tech_list))
    
    kwargs["valid_loc_techs"] = valid_loc_techs
    # We kept demand and export techs in for the 'valid loc techs'. We remove them here.
    # energy_caps = energy_caps[energy_caps.index.get_level_values("techs").str.find("demand") == -1]
    # energy_caps = energy_caps[energy_caps.index.get_level_values("techs").str.find("distribution_export") == -1]
    energy_caps = df_subset(energy_caps,tech_list_to_remove)
    
    output_costs = pd.concat(
        [get_output_costs(model, **kwargs) for model in model_dict.values()],
        keys=model_dict.keys(), names=new_dimension_name
    )
    if "co2" in cost_optimal_model._model_data.costs.values:
        co2_kwargs = {"cost_class": "co2", "unit": "MtCO2", "mapping": EMISSIONS_NAME_MAPPING, **kwargs}
        all_data_dict.update(get_input_costs(cost_optimal_model.inputs, **co2_kwargs))
        _output_emissions = {}
        for model_name, model in model_dict.items():
            if "co2" in model._model_data.costs.values:
                _output_emissions[model_name] = get_output_costs(model, **co2_kwargs)
        output_emissions = pd.concat(
            _output_emissions.values(), keys=_output_emissions.keys(), names=new_dimension_name
        )
        dataframe_to_dict_elements(output_emissions, all_data_dict)

    energy_flows = pd.concat(
        [get_flows(model, None, **kwargs) for model in model_dict.values()],
        keys=model_dict.keys(), names=new_dimension_name,
    )
    energy_flows_sum = agg_flows(energy_flows, "sum")
    energy_flows_max = agg_flows(energy_flows, "max")
    energy_flows_monthly_sum = agg_flows(energy_flows, "sum", "1M")
    energy_flows_monthly_max = agg_flows(energy_flows, "max", "1M")

    get_transmission_data(all_data_dict, model_dict, new_dimension_name, **kwargs)
    
    # energy_caps = add_units_to_caps(energy_caps, energy_flows_max, cost_optimal_model)
    carrier_dict, unit_dict = get_carrier_unit_per_energy_cap(energy_flows_max)
    energy_caps_primary_carrier = adding_carrier_unit_to_energy_cap(energy_caps, unit_dict, carrier_dict, ZERO_THRESHOLD)
    energy_caps_from_flows = add_units_all_caps(energy_flows_max, timestep)
    energy_caps_all_carriers = get_final_energy_cap(energy_caps_primary_carrier, energy_caps_from_flows, energy_flows_sum, ZERO_THRESHOLD)
    # all_data_dict["nameplate_capacity_primary_carrier"]=energy_caps_primary_carrier

    """
    energy_caps = pd.concat(
        [get_energy_caps(model) for model in model_dict.values()],
        keys=model_dict.keys(), names=new_dimension_name,
    )
    """

    storage_caps = add_storage_carriers(
        pd.concat(
            [get_storage_caps(model, **kwargs) for model in model_dict.values()],
            keys=model_dict.keys(), names=new_dimension_name,
        ),
        energy_flows_max["flow_out_max"]
    )
    if return_hourly:
        storage = add_storage_carriers(
            pd.concat(
                [get_storage(model, **kwargs) for model in model_dict.values()],
                keys=model_dict.keys(), names=new_dimension_name,
            ),
        energy_flows["flow_out"]
        )
    
    energy_caps_all_carriers.index.get_level_values("techs").unique()
    names = names.reindex(energy_caps_all_carriers.index.get_level_values("techs").unique()).fillna(NEW_TECH_NAMES).fillna(OLD_TECH_NAMES)
    # assert names.isna().sum() == 0

    for df in [
        output_costs, energy_caps_all_carriers, energy_caps_primary_carrier, energy_flows_sum, energy_flows_max,
        energy_flows_monthly_sum, energy_flows_monthly_max, storage_caps
    ]:
        dataframe_to_dict_elements(df, all_data_dict)

    if return_hourly:
        dataframe_to_dict_elements(energy_flows, all_data_dict)
        dataframe_to_dict_elements(storage, all_data_dict)
    else:
        del all_data_dict["net_import"]
        
    # delate nan values (included already in the package writing command of friendly data library
    
    for keys in all_data_dict.keys():
        all_data_dict[keys] = all_data_dict[keys].dropna()

    all_data_dict["names"] = names

    return all_data_dict

def dataframe_to_dict_elements(df, data_dict):
    """DF to dict of series, with key names == column names"""
    data_dict.update({col_name: df.loc[:, col_name] for col_name in df.columns})


def get_energy_caps(model, **kwargs):
    """Get energy capacity"""
    mapped_da = map_da(model._model_data["energy_cap"], keep_demand=True, **kwargs)
    series = clean_series(mapped_da, zero_threshold=ZERO_THRESHOLD)
    if series is None:
        return None
    else:
        return (
            series
            .sum(level=["techs", "locs"])
            .to_frame("nameplate_capacity")
            .div(10)
        )

def get_storage_caps(model, **kwargs):
    """Get storage capacity"""
    mapped_da = map_da(model._model_data["storage_cap"], keep_demand=False, **kwargs)
    series = clean_series(mapped_da, **kwargs)
    if series is None:
        return None
    else:
        return (
            series
            .sum(level=["techs", "locs"])
            .to_frame("storage_capacity")
            .assign(unit="twh")
            .set_index("unit", append=True)
            .div(10)
        )


def get_storage(model, **kwargs):
    """Get storage level as a function of time"""
    mapped_da = map_da(model._model_data["storage"], timeseries_agg=None, **kwargs)
    return (
        clean_series(mapped_da, **kwargs)
        .div(10)
        .to_frame("storage_level")
        .assign(unit="twh")
        .set_index("unit", append=True)
    )


def get_valid_loc_techs(df):
    return df.index.get_level_values("locs") + "::" + df.index.get_level_values("techs")

def get_valid_techs(df):
    return df.index.get_level_values("techs")

def get_a_flow(model, flow_direction, timeseries_agg, **kwargs):
    mapped_da = map_da(
        model._model_data[f"carrier_{flow_direction}"], timeseries_agg=timeseries_agg, **kwargs
    )
    return (
        clean_series(mapped_da, **kwargs)
        .div(10)
        .abs()
        .to_frame(flow_name(flow_direction, timeseries_agg))
        .assign(unit='twh')
        .reset_index()
    )


def flow_name(flow_direction, timeseries_agg):
    direction = "out" if flow_direction == "prod" else "in"
    return f"flow_{direction}_{timeseries_agg}" if timeseries_agg is not None else f"flow_{direction}"


def agg_flows(energy_flows_df, timeseries_agg, final_resolution=None, **kwargs):

    flows_df = energy_flows_df.rename_axis(columns="flows").stack().unstack("timesteps")

    if timeseries_agg != "sum":
        if "timestep_resolution" in kwargs.keys():
            flows_df = flows_df.div(kwargs["timestep_resolution"])
        agg_kwargs = {}
    else:
        agg_kwargs = {"min_count": 1}
    if final_resolution is not None:
        flow_agg = flows_df.resample(final_resolution, axis=1).apply(timeseries_agg, **agg_kwargs).stack()
        flow_agg = flow_agg.rename(lambda x: f"{x}_{timeseries_agg}_{final_resolution}", level="flows")
    else:
        flow_agg = flows_df.apply(timeseries_agg, **agg_kwargs, axis=1)
        flow_agg = flow_agg.rename(lambda x: f"{x}_{timeseries_agg}", level="flows")
    return flow_agg.unstack("flows")


def get_flows(model, timeseries_agg, **kwargs):
    prod = get_a_flow(model, "prod", timeseries_agg, **kwargs)
    con = get_a_flow(model, "con", timeseries_agg, **kwargs)

    prod.loc[prod.techs.str.find('transport_') > -1, 'unit'] = 'billion_km'
    con.loc[con.techs.isin(['demand_heavy_transport', 'demand_light_transport']), 'unit'] = 'billion_km'
    for df in [prod, con]:
        df.loc[df.carriers.isna(), "unit"] = np.nan
        df.loc[df.carriers == 'co2', "unit"] = '100kt'
    if timeseries_agg is None:
        levels = ["techs", "locs", "carriers", "unit", "timesteps"]
    else:
        levels = ["techs", "locs", "carriers", "unit"]
    flow = pd.concat(
        [i.set_index(levels).iloc[:, 0] for i in [prod, con]],
        axis=1
    )
    return flow


def get_transmission_data(data_dict, model_dict, new_dimension_name, **kwargs):
    kwargs["valid_loc_techs"] = None
    region_group = kwargs.get("region_group", "countries")
    _from = "exporting_region"
    _to = "importing_region"

    def _rename_remote(series_or_df, level):
        df = series_or_df.reset_index(level)
        if (df[level].str.find(":") > -1).any():
            remote = df[level].str.split(":", expand=True)[1]
        else:
            remote = df[level]
        df[level] = rename_locations(remote, region_group)
        return df.set_index(level, append=True)

    def _rename_tech(x):
        if x.startswith("ac"):
            tech_name = "ac_transmission"
        elif x.startswith("dc"):
            tech_name = "dc_transmission"
        elif x.startswith("co2_transmission"):
            tech_name = "co2_transmission"
        elif x.startswith("co2_tanker"):
            tech_name = "co2_tanker"
        else:
            tech_name = "unrecognised"
        return tech_name
        
    def _get_unit(x):
        if "transmission" in x:
            unit = "tw"
        elif "co2" in x:
            unit = "100kt"
        else:
            unit = "n.a."
        return unit
        
    def _get_carrier(x):
        if "transmission" in x:
            unit = "electricity"
        elif "co2" in x:
            unit = "co2"
        else:
            unit = "n.a."
        return unit
        
    def _get_transmission_flows(model, timeseries_agg, **kwargs):
        flows = get_flows(model, timeseries_agg, transmission_only=True, **kwargs)

        index_names = flows.rename_axis(index={"techs": _from, "locs": _to}).index.names
        summed_flows = []
        for flow in ["prod", "con"]:
            _flow = flows[flow_name(flow, timeseries_agg)]
            remote_loc = _to if flow == "con" else _from
            loc = _from if flow == "con" else _to
            _flow = (
                _rename_remote(_flow, level="techs")
                .rename_axis(index={"techs": remote_loc, "locs": loc})
            )
            _flow_summed_across_all_transmission_techs = _flow.groupby(level=index_names).sum()
            summed_flows.append(_flow_summed_across_all_transmission_techs)

        # take the mean, which averages over transmission losses in either direction along a link
        transmission = pd.concat(summed_flows, axis=1).mean(axis=1)
        import_export = pd.concat(
            [
                transmission,
                transmission
                .rename_axis(index={_from: _to, _to: _from})
                .reorder_levels(transmission.index.names)
            ],
            axis=1, keys=["import", "export"], sort=True
        )

        net_import = import_export["import"] - import_export["export"]
        net_import[net_import.abs() < ZERO_THRESHOLD] = 0

        return net_import

    def _get_transmission_caps(model, **kwargs):
        mapped_da = map_da(model._model_data["energy_cap"], keep_demand=False, transmission_only=True, **kwargs)
        df = clean_series(mapped_da, zero_threshold=ZERO_THRESHOLD).unstack("locs")
        df.index = df.index.str.split(":", expand=True).rename(["techs", _from])
        series = (
            _rename_remote(df, level=_from)
            .rename(_rename_tech, level="techs")
            .rename_axis(columns=_to)
            .assign(unit=lambda x: x.index.get_level_values('techs').map(_get_unit), carriers=lambda x: x.index.get_level_values('techs').map(_get_carrier))  #.assign(unit="tw",carriers="electricity")
            .set_index(["unit", "carriers"], append=True)
            .stack()
            .div(10)
        )
        return series.groupby(level=series.index.names).sum()

    def _get_transmission_costs(model, **kwargs):
        cost_class = "monetary"
        unit = "billion_2015eur"
        mapped_da = map_da(model._model_data["cost"].loc[{"costs": cost_class}], keep_demand=False, transmission_only=True, **kwargs)
        df = clean_series(mapped_da, zero_threshold=ZERO_THRESHOLD).unstack("locs")
        df.index = df.index.str.split(":", expand=True).rename(["techs", _from])
        series = (
            _rename_remote(df, level=_from)
            .rename(_rename_tech, level="techs")
            .rename_axis(columns=_to)
            .assign(unit=unit)
            .set_index("unit", append=True)
            .stack()
        )
        return series.groupby(level=series.index.names).sum()

    def _concat_from_to(index):
        return index.get_level_values(_from) + "::" + index.get_level_values(_to)

    def _clean_flows(flow, valid_connections):
        return flow.where(_concat_from_to(flow.index).isin(valid_connections)).dropna()

    caps = pd.concat(
        [_get_transmission_caps(model, **kwargs) for model in model_dict.values()],
        keys=model_dict.keys(), names=new_dimension_name,
    )
    flows = pd.concat(
        [_get_transmission_flows(model, None, **kwargs) for model in model_dict.values()],
        keys=model_dict.keys(), names=new_dimension_name,
    )
    flows_sum = agg_flows(flows.to_frame("net_import"), "sum").squeeze()
    flows_monthly_sum = agg_flows(flows.to_frame("net_import"), "sum", "1M").squeeze()
    flows_max = agg_flows(flows.to_frame("net_import"), "max").squeeze()
    flows_monthly_max = agg_flows(flows.to_frame("net_import"), "max", "1M").squeeze()

    costs = pd.concat(
        [_get_transmission_costs(model, **kwargs) for model in model_dict.values()],
        keys=model_dict.keys(), names=new_dimension_name,
    )

    valid_connections = _concat_from_to(caps.index).drop_duplicates()

    data_dict["net_transfer_capacity"] = caps
    data_dict["net_import"] = _clean_flows(flows, valid_connections)
    data_dict["net_import_sum"] = _clean_flows(flows_sum, valid_connections)
    data_dict["net_import_sum_1M"] = _clean_flows(flows_monthly_sum, valid_connections)
    data_dict["net_import_max"] = _clean_flows(flows_max, valid_connections)
    data_dict["net_import_max_1M"] = _clean_flows(flows_monthly_max, valid_connections)
    data_dict["total_transmission_costs"] = _clean_flows(costs, valid_connections)


def map_da(da, keep_demand=True, timeseries_agg="sum", loc_tech_agg="sum", **kwargs):
    loc_tech_dim = [i for i in da.dims if "loc_tech" in i][0]
    mapped_da = get_cleaned_dim_mapping(da, loc_tech_dim, keep_demand, loc_tech_agg, **kwargs)
    if "timesteps" in mapped_da.dims and timeseries_agg is not None:
        return agg_da(mapped_da, timeseries_agg, "timesteps", **kwargs)
    else:
        return mapped_da


def clean_series(da, zero_threshold=0, valid_loc_techs=None, **kwargs):
    """
    Get series from dataarray in which we clean out useless info.

    Parameters
    ----------
    da : xr DataArray
        DataArray that has already been prepared for turning into a clean series using "map_da"
    zero_threshold : float
        Value above which all valid data lies.
        Anything below this in absolute magnitude will be deemed as invalid and removed from the data.
        This exists to remove the small values left over from the Barrier LP method.
    """
    series = da.to_series()
    clean_series = (
        series
        .where(lambda x: (~np.isinf(x)) & (abs(x) > zero_threshold))
        .dropna()
    )
    if valid_loc_techs is not None:
        clean_series = slice_on_loc_techs(clean_series, valid_loc_techs)
    if clean_series.empty:
        return None
    else:
        return clean_series


def slice_on_loc_techs(series, loc_techs):
    return (
        series
        .where((
            series.index.get_level_values("locs") +
            "::" + series.index.get_level_values("techs")
        ).isin(loc_techs))
        .dropna()
    )


def add_storage_carriers(storage_df, energy_flows):
    _flows = energy_flows.reset_index("carriers")
    _flows = _flows[~_flows.index.duplicated()]
    carriers = (
        _flows
        .reorder_levels(storage_df.index.names)
        .reindex(storage_df.index)
        .carriers
    )
    return (
        storage_df
        .assign(carriers=carriers)
        .set_index("carriers", append=True)
        .reorder_levels(energy_flows.index.names)
    )

def get_carrier_unit_per_energy_cap(energy_flows_max):
    energy_flow = energy_flows_max["flow_out_max"].reset_index()
    # energy_flow = energy_flow.dropna()
    energy_flow = energy_flow[["techs", "carriers", "unit"]]
    energy_flow = energy_flow.drop_duplicates(keep='first')

    df = copy.deepcopy(energy_flow)

    df.loc[(df.unit == 'twh'),'unit']='tw'
    df.loc[(df.unit == 'billion_km'),'unit']='billion_km_per_hour'
    df.loc[(df.unit == '100kt'),'unit']='100kt_per_hour'
    df = df.reset_index(drop=True)

    list_keys = list(df["techs"])
    list_carriers = list(df["carriers"])
    list_unit = list(df["unit"])

    carrier_dict = dict(zip(list_keys, list_carriers))
    unit_dict = dict(zip(list_keys, list_unit))

    return carrier_dict, unit_dict

def add_tech_carriers(tech_df, energy_flows): #mi sa da togliere
    _flows = energy_flows.reset_index("carriers")
    _flows = _flows[~_flows.index.duplicated()]
    carriers = (
        _flows
        .reorder_levels(tech_df.index.names)
        .reindex(tech_df.index)
        .carriers
    )
    return (
        tech_df
        .assign(carriers=carriers)
        .set_index("carriers", append=True)
        .reorder_levels(energy_flows.index.names)
    )

def add_units_nameplate_capacity(energy_caps):
    energy_caps_unit = energy_caps.reset_index("techs")
    energy_caps_unit["unit"]="tw"
    energy_caps_unit.loc[energy_caps_unit.techs.str.find('transport_') > -1, 'unit'] = 'billion_km'
    energy_caps_unit.loc[energy_caps_unit.techs.str.find('dac') > -1, 'unit'] = '100kt'
    energy_caps_unit.loc[energy_caps_unit.techs.str.find('demand_co2') > -1, 'unit'] = '100kt'
    energy_caps_unit = energy_caps_unit.set_index(["techs","unit"], append=True)
    
    return energy_caps_unit

def add_units_all_caps(energy_flows_max, timestep):
    # In this dataframe, all the non-primary output energy outflows are included.
    energy_caps_from_flows = energy_flows_max["flow_out_max"].dropna()/timestep
    energy_caps_from_flows = energy_caps_from_flows.rename(lambda x: "tw" if x == "twh" else x + "_per_hour", level="unit")
    energy_caps_from_flows= energy_caps_from_flows.to_frame().rename(columns={"flow_out_max":"nameplate_capacity"})
    
    return energy_caps_from_flows


def adding_carrier_unit_to_energy_cap(energy_caps, unit_dict, carrier_dict, ZERO_THRESHOLD):
    _energy_caps = energy_caps.reset_index("techs")
    _energy_caps["carriers"]=_energy_caps["techs"].map(lambda x: carrier_dict[x])
    _energy_caps["unit"]=_energy_caps["techs"].map(lambda x: unit_dict[x])
    _energy_caps = _energy_caps.set_index("techs", append=True)
    _energy_caps = _energy_caps.set_index("carriers", append=True)
    _energy_caps = _energy_caps.set_index("unit", append=True)
    energy_caps_carrier_unit = _energy_caps.reorder_levels([0,2,1,3,4])
    energy_caps_carrier_unit = energy_caps_carrier_unit[energy_caps_carrier_unit["nameplate_capacity"] > ZERO_THRESHOLD]
    energy_caps_carrier_unit = energy_caps_carrier_unit.rename(columns={"nameplate_capacity":"nameplate_capacity_primary_carrier"})

    return energy_caps_carrier_unit


def adding_carrier_to_energy_caps(energy_caps_unit, singlecarrier_techs_dict, multicarrier_techs_dict, loc_newtech_dict):
    tech_carrier_dict = {**multicarrier_techs_dict, **singlecarrier_techs_dict, **loc_newtech_dict}
    energy_caps_unit_carrier = energy_caps_unit.reset_index("techs")
    energy_caps_unit_carrier["carrier"]=energy_caps_unit_carrier["techs"].map(lambda x: tech_carrier_dict[x])

    return energy_caps_unit_carrier

def add_units_to_caps(energy_caps, energy_flows, cost_optimal_model):
    """
    Get units for nameplate capacities and add additional capacities for multi-carrier
    technologies, to give an approximate maximum capacity for non-primary carriers.
    """
    # print(cost_optimal_model.inputs)
    
    
    multicarrier_primary_info = split_loc_techs(
        cost_optimal_model.inputs.lookup_primary_loc_tech_carriers_out,
        return_as="Series"
    )
    multicarrier_primary_info = (
        multicarrier_primary_info
        .str
        .split("::", expand=True)[2]
        .to_frame("carriers")
    )
    multicarrier_primary_info = (
        multicarrier_primary_info
        .replace({
            x: x.split("_")[1] if ("_heat" in x or "_transport" in x or "syn_" in x) else x
            for x in np.unique(multicarrier_primary_info.values)
        })
        .groupby(level="techs").first()
        .set_index("carriers", append=True)
    )
    
    flows_out_reset_carriers = energy_flows["flow_out_max"].dropna().reset_index("carriers")
    secondary_carrier = (
        flows_out_reset_carriers
        [flows_out_reset_carriers.index.duplicated(keep=False)]
        .set_index("carriers", append=True)
        .squeeze()
        .unstack(["techs", "carriers"])
        .drop(multicarrier_primary_info.index, errors="ignore", axis=1)
        .stack(["techs", "carriers"])
        .reorder_levels(energy_flows.index.names)
    )
    
    # flows_out_reset_carriers = energy_flows["flow_out_max"].dropna().reset_index("carriers")
    # dataframe = flows_out_reset_carriers[flows_out_reset_carriers.index.duplicated(keep=False)].set_index("carriers", append=True).squeeze().unstack(["techs", "carriers"]).stack(["techs", "carriers"])
    
    all_primary_carrier = energy_flows["flow_out_max"].dropna().drop(secondary_carrier.index)
    secondary_carrier = secondary_carrier.rename(lambda x: "tw" if x == "twh" else x + "_per_hour", level="unit")
    all_primary_carrier = all_primary_carrier.rename(lambda x: "tw" if x == "twh" else x + "_per_hour", level="unit")

    energy_caps_with_primary_units = energy_caps.align(all_primary_carrier,axis=0)[0].dropna()
    assert len(energy_caps_with_primary_units) == len(energy_caps)

    energy_caps_with_all_units = (
        energy_caps_with_primary_units
        .append(secondary_carrier.to_frame("nameplate_capacity"))
        .sort_index()
    )

    assert energy_caps_with_all_units.reindex(energy_caps_with_primary_units.index).equals(energy_caps_with_primary_units)

    return energy_caps_with_all_units

def get_final_energy_cap(energy_cap_primary, energy_cap_all, energy_flows_sum, ZERO_THRESHOLD): #to be added
    # # energy_cap_primary: energy_caps_primary_carrier
    # # energy_cap_all: energy_caps_from_flows
    # energy_cap_primary = energy_cap_primary.rename(columns={"nameplate_capacity_primary_carrier":"nameplate_capacity"})
    # energy_cap_df = energy_cap_primary.append(energy_cap_all)
    # energy_cap_df = energy_cap_df[~energy_cap_df.index.duplicated(keep='first')]
    # energy_cap_df = energy_cap_df[energy_cap_df["nameplate_capacity"] > ZERO_THRESHOLD]
    
    # Obtain nameplate capacity
    energy_cap_primary = energy_cap_primary.rename(columns={"nameplate_capacity_primary_carrier":"nameplate_capacity"})
    energy_cap_df = energy_cap_primary.append(energy_cap_all)
    energy_cap_df = energy_cap_df[~energy_cap_df.index.duplicated(keep='first')]
    energy_cap_df = energy_cap_df[energy_cap_df["nameplate_capacity"] > ZERO_THRESHOLD]

    # Ugly search for all possible combinations of technology and carrier.
    # My heart weeps at the sight of this thing.
    energy_cap_df = energy_cap_df.reset_index()
    energy_cap_df["flow"] = np.nan

    flow_search = energy_flows_sum.reset_index()
    for tech in energy_cap_df["techs"].unique():
        for carrier in energy_cap_df["carriers"].unique():
            cap_slice = energy_cap_df[(energy_cap_df["techs"] == tech) & (energy_cap_df["carriers"] == carrier)].copy()
            if not cap_slice.empty:
                flow_info = flow_search[(flow_search["techs"] == tech) & (flow_search["carriers"] == carrier)].iloc[0]
                # Identify flow direction
                if not np.isnan(flow_info["flow_in_sum"]) and not np.isnan(flow_info["flow_out_sum"]):
                    cap_slice["flow"] = "both"
                elif not np.isnan(flow_info["flow_in_sum"]):
                    cap_slice["flow"] = "in"
                elif not np.isnan(flow_info["flow_out_sum"]):
                    cap_slice["flow"] = "out"
                else:
                    raise ValueError("This technology has no output in either direction. Thus, I explode with massive force.")
                energy_cap_df.update(cap_slice)
    energy_cap_df = energy_cap_df.set_index(["scenario", "techs", "locs", "carriers", "unit", "flow"])
    return energy_cap_df    


def get_output_costs(
    model, cost_class="monetary", unit="billion_2015eur", mapping=COST_NAME_MAPPING, **kwargs
):
    """
    Get costs associated with model results
    """
    costs = {}
    for _cost in ["cost", "cost_investment", "cost_var"]:
        cost_da = model._model_data[_cost].loc[{"costs": cost_class}]
        mapped_da = map_da(cost_da, keep_demand=True, **kwargs) # keep_demand = False

        cost_series = clean_series(mapped_da, **kwargs)
        if cost_series is None:
            continue
        else:
            costs[mapping[_cost]] = (
                cost_series
                .to_frame(unit)
                .rename_axis(columns="unit")
                .stack()
            )
    return pd.concat(costs.values(), keys=costs.keys(), axis=1)


def get_input_costs(
    inputs, cost_class="monetary", unit="billion_2015eur", mapping=COST_NAME_MAPPING,
    **kwargs
):
    """
    Get costs used as model inputs
    """
    costs = {}
    for var_name, var_data in inputs.data_vars.items():
        if "costs" not in var_data.dims or not var_name.startswith("cost"):
            continue

        if "cap" in var_name:
            _unit = f"{unit}_per_tw"
        elif var_name == "cost_om_annual":
            _unit = f"{unit}_per_tw_per_year"
        elif var_name == "cost_om_annual_investment_fraction":
            _unit = "fraction_of_total_investment"
        elif var_name == "cost_depreciation_rate":
            _unit = "fraction"
        elif "om_" in var_name:
            _unit = f"{unit}_per_twh"
        _name = mapping[var_name]
        mapped_da = map_da(var_data.loc[{"costs": cost_class}], loc_tech_agg="mean", **kwargs)
        series = clean_series(mapped_da)
        if series is not None:
            costs[_name] = (
                series
                .to_frame(_unit)
                .rename_axis(columns="unit")
                .stack()
            )
            costs[_name].loc[costs[_name].index.get_level_values("unit").str.find("per_tw") > -1] *= 10

    return costs


def rename_locations(locations, region_group):
    if region_group == "countries":
        return locations.str.split("_", expand=True)[0]
    else:
        return locations.replace(region_group)

def get_multicarrier_techs(tech_carrier_df): # TO BE REMOVED
    multicarrier_techs = tech_carrier_df[tech_carrier_df.duplicated('tech', keep=False) == True]
    multicarrier_techs_dict = {}    
    for tech in multicarrier_techs.tech:
        multicarrier_techs_dict[tech]=list(multicarrier_techs.loc[multicarrier_techs.tech == tech]["carrier"].values)
    
    return multicarrier_techs_dict

def get_singlecarrier_techs(tech_carrier_df): # TO BE REMOVED
    singlecarrier_techs = tech_carrier_df[tech_carrier_df.duplicated('tech', keep=False) == False]
    singlecarrier_techs = singlecarrier_techs.set_index(['tech'])
    singlecarrier_techs_dict = singlecarrier_techs.to_dict()['carrier']
    
    return singlecarrier_techs_dict

def get_tech_carrier_df(model): # TO BE REMOVED
    loc_tech_carrier = pd.Series(model._model_data.loc_tech_carriers_prod.values)
    loc_tech_carrier_split = loc_tech_carrier.str.split("::",expand=True)
    loc_tech_carrier_split.rename(columns={0: 'region', 1: 'tech', 2: "carrier"}, inplace=True)
    region_1 = list(loc_tech_carrier_split["region"])[0]
    tech_carrier_df = loc_tech_carrier_split[loc_tech_carrier_split.region == region_1].iloc[:,1:].sort_values(by="tech",kind="mergesort")

    return tech_carrier_df

def get_cleaned_dim_mapping(
    da, dim, keep_demand=True, dim_agg="sum",
    region_group="countries", transmission_only=False, **kwargs
):
    """
    Go from a concatenated location::technology(::carrier) list into an unconcatenated
    list, including summing up sub-national regions to the national level and technologies
    which are model artefacts to technologies which are have a real 'equivalent'.

    Parameters
    ----------
    da : xarray DataArray
    dim : string
        The concatenated dimension in `da` to unconcatenate
    keep_demand : bool, default = True
        If true, keep demand 'technologies' in the output
    dim_agg : string, default = "sum"
        How to group the unconcatenated and cleaned up data.
        Any xarray groupby method can be passed.
    region_group : string or mapping, default = "countries"
        If "countries", group locations to a country level, otherwise group based on
        a mapping from model locations to group names. Mapping allows e.g. one country to
        remain as sub-country regions, while all others are grouped to countries or 'rest'
    """
    split_dim = da[dim].to_series().str.split("::", expand=True)
    split_dim[0] = rename_locations(split_dim[0], region_group)
    if transmission_only:
        split_dim = split_dim[split_dim[1].str.find(":") > -1]
    else:
        split_dim = split_dim[split_dim[1].str.find(":") == -1]
    split_dim = split_dim.loc[
        (split_dim[1].str.find("tech_heat") == -1) & (split_dim[1].str.find("_converter") == -1)
    ]
    if keep_demand is False:
        split_dim = split_dim.loc[split_dim[1].str.find("demand") == -1]

    heat_storage = split_dim.loc[split_dim[1].str.find("heat_storage") > -1, 1]
    if not heat_storage.empty:
        split_dim.loc[split_dim[1].str.find("_heat_storage") > -1, 1] = (
            "heat_storage" + heat_storage.str.partition("heat_storage")[2]
        )
    split_dim.loc[split_dim[1].str.startswith("wind_onshore"), 1] = "wind_onshore"

    if "carriers" in dim:
        split_dim.loc[split_dim[2].str.endswith("_heat"), 2] = "heat"
        split_dim.loc[split_dim[2].str.endswith("co2_transport"), 2] = "co2_pipeline" # to be removed
        split_dim.loc[split_dim[2].str.endswith("_transport"), 2] = "transport" # removed for PATHFNDR to keep heavy and light duty vehicles separated
        for fuel in ["diesel", "kerosene", "methane", "methanol"]:
            split_dim.loc[split_dim[2] == f"syn_{fuel}", 2] = fuel
        new_dim = ("locs", "techs", "carriers")
    else:
        new_dim = ("locs", "techs")

    split_dim["new_dim"] = list(split_dim.itertuples(index=False, name=None))
    new_da = da.loc[{dim: split_dim.index}]
    new_da = agg_da(new_da.groupby(xr.DataArray.from_series(split_dim["new_dim"])), dim_agg)
    new_da.coords["new_dim"] = pd.MultiIndex.from_tuples(new_da.coords["new_dim"].to_index(), names=new_dim)

    return new_da


def agg_da(da, agg_method, agg_dim=None, **kwargs):
    """
    Aggregate `agg_dim` dimension of an xarray DataArray `da`,
    including setting 'min_count=1' if `agg_method` is "sum"
    """
    if agg_dim == "timesteps" and "timestep_resolution" in kwargs.keys() and agg_method != "sum":
        da = da / kwargs["timestep_resolution"]
    agg_kwargs = {"keep_attrs": True}
    if agg_method == "sum":
        agg_kwargs.update({"min_count": 1})
    return getattr(da, agg_method)(agg_dim, **agg_kwargs)
    
def subfinder(mylist, pattern):
    matches = []
    for i in range(len(mylist)):
        if mylist[i] == pattern[0] and mylist[i:i+len(pattern)] == pattern:
            matches.append(pattern)
    return matches

def df_subset(dataframe, tech_list):
    dataframe_sorted = copy.deepcopy(dataframe)
    for tech in tech_list:
        dataframe_sorted = dataframe_sorted[dataframe_sorted.index.get_level_values("techs") != tech]
    return dataframe_sorted
    
def tech_list_subset(dataframe,keyword):
    tech_list = list((dataframe[dataframe.index.get_level_values("techs").str.find(keyword) == 0]).index.get_level_values("techs").unique())
    return tech_list
    
"""    pass more than one keyword to save the techs in a sinle list
def tech_list_subset(dataframe,keyword,**kwargs):
    keyword_list = keyword.append(**kwargs)
    
    for k in keyword_list
    tech_list = list((dataframe[dataframe.index.get_level_values("techs").str.find(keyword) == 0]).index.get_level_values("techs").unique())
    
    return tech_list
"""    
    