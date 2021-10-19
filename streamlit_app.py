import streamlit as st
import pandas as pd
import altair as alt
from vega_datasets import data

st.set_page_config(layout="wide")

state2id = {'AL':1, 'AK':2, 'AZ':4, 'AR':5, 'CA':6, 'CO':8, 'CT':9, 'DE':10, 'DC':11, 'FL':12, 'GA':13, 'HI':15, 
           'ID':16, 'IL':17, 'IN':18, 'IA':19, 'KS':20, 'KY':21, 'LA':22, 'ME':23, 'MD':24, 'MA':25, 'MI':26, 'MN':27,
           'MS':28, 'MO':29, 'MT':30, 'NE':31, 'NV':32, 'NH':33, 'NJ':34, 'NM':35, 'NY':36, 'NC':37, 'ND':38, 'OH':39,
           'OK':40, 'OR':41, 'PA':42, 'RI':44, 'SC':45, 'SD':46, 'TN':47, 'TX':48, 'UT':49, 'VT':50, 'VA':51, 'WA':53,
           'WV':54, 'WI':55, 'WY':56
}

state2abbr = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}
    
# invert the dictionary
abbr2state = dict(map(reversed, state2abbr.items()))
state_list = list(state2abbr.keys())
state_list.pop(1)

@st.cache
def load_election_data():
    election_pd = pd.read_csv("data/president_election.csv")
    state_vote = election_pd.groupby(['state_abbr'], as_index=False) \
        .agg({'votes_dem_2016': 'sum', 'votes_gop_2016': 'sum', 'total_votes_2016': 'sum'})
    state_vote['dem_lead_percent'] = (state_vote['votes_dem_2016'] - state_vote['votes_gop_2016']) \
        / state_vote['total_votes_2016'] * 100
    state_vote = state_vote.round(2)
    state_vote['id'] = state_vote.apply(lambda row: state2id[row['state_abbr']], axis=1)
    state_vote['state'] = state_vote.apply(lambda row: abbr2state[row['state_abbr']], axis=1)
    election_pd['state'] = election_pd.apply(lambda row: abbr2state[row['state_abbr']], axis=1)
    return election_pd, state_vote

@st.cache
def load_census_data():
    census_df = pd.read_csv("data/acs2017_county_data.csv")
    census_df = census_df[["CountyId", "State", "County", "TotalPop", "Hispanic", "White", \
                        "Black", "Native", "Asian", "Pacific", "Income", "Poverty"]]
    census_df = census_df[census_df["State"] != "Puerto Rico"]
    census_df["Other Race"] = census_df["Native"] + census_df["Asian"] + census_df["Pacific"]
    census_df = census_df.drop(columns=["Native", "Asian", "Pacific"])

    # Summarize County data into state data
    census_df["Total Hispanic"] = census_df["TotalPop"] * census_df["Hispanic"]
    census_df["Total White"] = census_df["TotalPop"] * census_df["White"]
    census_df["Total Black"] = census_df["TotalPop"] * census_df["Black"]
    census_df["Total Income"] = census_df["TotalPop"] * census_df["Income"]
    census_df["Total Poverty"] = census_df["TotalPop"] * census_df["Poverty"]
    census_df["Total Other Race"] = census_df["TotalPop"] * census_df["Other Race"]

    state_census = census_df.groupby("State", as_index=False).agg({"TotalPop":"sum", "Total White":"sum", "Total Hispanic": "sum",\
                    "Total Black":"sum", "Total Income":"sum", "Total Poverty":"sum", "Total Other Race":"sum"})
    state_census["Hispanic"] = state_census["Total Hispanic"] / state_census["TotalPop"]
    state_census["White"] = state_census["Total White"] / state_census["TotalPop"]
    state_census["Black"] = state_census["Total Black"] / state_census["TotalPop"]
    state_census["Income"] = state_census["Total Income"] / state_census["TotalPop"]
    state_census["Poverty"] = state_census["Total Poverty"] / state_census["TotalPop"]
    state_census["Other Race"] = state_census["Total Other Race"] / state_census["TotalPop"]
    state_census = state_census.drop(columns=["Total Hispanic", "Total White", "Total Black", \
                                          "Total Income", "Total Poverty", "Total Other Race"])
    census_df = census_df.drop(columns=["Total Hispanic", "Total White", "Total Black", \
                                        "Total Income", "Total Poverty", "Total Other Race"])
    state_census['id'] = state_census.apply(lambda row: state2id[state2abbr[row['State']]], axis=1)
    state_census = state_census.rename(columns={"TotalPop":"TotalPopulation"})
    census_df = census_df.rename(columns={"TotalPop":"TotalPopulation"})

    census_df = census_df.round(2)
    state_census = state_census.round(2)
    return census_df, state_census

def state_level_election_graph(data, state, county_map):
    state_data = data[data['state'] == state]
    state_data["dem_lead_percent"] = (state_data["votes_dem_2016"] - state_data["votes_gop_2016"]) / state_data["total_votes_2016"] * 100
    largest_diff = state_data["dem_lead_percent"].abs().max()
    state_data = state_data.round(2)
    graph = alt.Chart(county_map).mark_geoshape().encode(
        color=alt.Color('dem_lead_percent:Q', scale=alt.Scale(type='linear',domain=[-largest_diff, largest_diff],scheme='redblue')),
        tooltip=['county_name:N', 'dem_lead_percent:Q'],
    ).transform_lookup(
        lookup='id',
        from_=alt.LookupData(state_data, 'FIPS', ['county_name','dem_lead_percent']),
    ).properties(
        width=600,
        height=400
    ).project(
        type='albersUsa'
    )
    return graph

# Load map data and dataframes
election_full_pd, state_vote_pd = load_election_data()
states_map = alt.topo_feature(data.us_10m.url, 'states')
counties_map = alt.topo_feature(data.us_10m.url, 'counties')
census_full_pd, state_census = load_census_data()

state_election_chart = alt.Chart(states_map).mark_geoshape().encode(
    color=alt.Color('dem_lead_percent:Q', scale=alt.Scale(type='linear',domain=[-48, 48],scheme='redblue')),
    tooltip=['state:N', 'dem_lead_percent:Q'],
).transform_lookup(
    lookup='id',
    from_=alt.LookupData(state_vote_pd, 'id', ['state','dem_lead_percent']),
).properties(
    width=750,
    height=400
).project(
    type='albersUsa'
)

st.title("Demographical and Economic Insights behind 2016 president election")
st.header("Introduction")
st.markdown("The president election of United States is a big shock for people around the world as "
            "Hillary Clinton lose the election despite leading position in all previous polling result."
            "In this application, we want to discover some insights from economic and demographical factors behind the election"
            "through visualization technique. We hope the country and state level visualizations can help people "
            "have better sense for the election at 2016. Also, this application is a good tool to have a basic "
            "understanding for United States's economic and demographical status. The dataset used in this "
            "application are collected from Kaggle: [election data](https://www.kaggle.com/joelwilson/2012-2016-presidential-elections), "
            "[census data](https://www.kaggle.com/muonneutrino/us-census-demographic-data).")

col1, col2= st.columns([1, 1])
with col1:
    st.header("Visualization of President Result")
    st.markdown("In this section, we provide the visualization of 2016 president election by lead of Democratic party in percent. ")
    st.subheader("Visualization of Election Result at Country Level")
    st.write(state_election_chart)

    st.subheader("Visualization of Election Result at State Level")
    election_selected_state = st.selectbox("Select a state to view election detail", state_list, key="state election", index=36)
    st.write(state_level_election_graph(election_full_pd, election_selected_state, counties_map))


with col2:
    st.header("Demographic and Economic Visualization")
    st.markdown("Here we provide several factors including: Total Population, white people population in percent, black people population in percent, Hispanic population in percent, "
            "other races population in percent, median income, and proverty rate in percent.")
    features_list = ["TotalPopulation", "Hispanic", "White", "Black", "Other Race", "Income", "Poverty"]

    st.subheader("Visualization of Factors at Country Level")
    selected_feature = st.selectbox("Select a factor to view", features_list, key="Econ/Demo Factor", index=0)

    census_state_chart = alt.Chart(states_map).mark_geoshape().encode(
        color=alt.Color('{}:Q'.format(selected_feature), scale=alt.Scale(type='linear')),
        tooltip=['State:N', '{}:Q'.format(selected_feature)],
    ).transform_lookup(
        lookup='id',
        from_=alt.LookupData(state_census, 'id', ['State', selected_feature]),
    ).properties(
        width=750,
        height=400
    ).project(
        type='albersUsa'
    )

    st.write(census_state_chart)

    st.subheader("Visualization of Factors at State Level")
    election_selected_state = st.selectbox("Select a state to view factor detail", state_list, key="state factor", index=36)
    census_county_chart = alt.Chart(counties_map).mark_geoshape().encode(
        color=alt.Color('{}:Q'.format(selected_feature), scale=alt.Scale(type='linear')),
        tooltip=['County:N', '{}:Q'.format(selected_feature)],
    ).transform_lookup(
        lookup='id',
        from_=alt.LookupData(census_full_pd[census_full_pd["State"] == election_selected_state], 'CountyId', ['County', selected_feature]),
    ).properties(
        width=500,
        height=300
    ).project(
        type='albersUsa'
    )
    st.write(census_county_chart)

st.header("Some Insights from Comparison")
st.markdown("At the country level, we cannot obtain a clear correlation between economic & demographical factor and election result. One "
            "Insight is that democratic lead state tend to have higher median income. However, at state level, we can obtain some clear correlations "
            "and insights. For nearly all the states, county with more dense population tends to favor democratic party. This observation confirm an opinion "
            "that most democratic part voters come from cities. Also, counties with more black population tend to support Hillary while counties with more "
            "white population are more likely to vote for Trump. In New York and California, counties with higher income tend to support Hillary. But in Illinois, "
            "the connection between income and election result is not significant.")
