
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# -----------------------------
# Configuration page
# -----------------------------
st.set_page_config(page_title="Indice climat 2040", layout="wide")

st.title("🌍 Où vivre en France en 2040 ?")

st.markdown(
"""
Cet indice combine trois dimensions climatiques :

- 🌡️ Température
- 🌊 Risque d'inondation
- 💧 Pression sur les ressources en eau
"""
)

# -----------------------------
# Chargement des données
# -----------------------------
temperature_df = pd.read_csv("pages/tables/Temperature_2040_df.csv")
flood_df = pd.read_csv("pages/tables/Flood_df.csv")
water_df = pd.read_csv("pages/tables/water_pressure_df.csv")


# -----------------------------
# Calcul scores individuels
# -----------------------------
temperature_df["score_temperature"] = (
    0.5 * temperature_df["nuits_tropicales"] +
    0.5 * temperature_df["jours_sup_35C"]
)

flood_df["score_flood"] = (
    0.7 * flood_df["score_scena_risque_normalise"] +
    0.3 * flood_df["score_land_perc"]
)

water_df["score_water"] = (
    0.4 * water_df["precipitations_ete"] +
    0.1 * water_df["indice_humidite_sol"] +
    0.3 * water_df["precipitations_annuelles"]+ 
    0.2 * water_df["Volume"]
)

# -----------------------------
# Fusion datasets
# -----------------------------
climate_df = (
    temperature_df[["code", "score_temperature"]]
    .merge(flood_df[["code", "score_flood"]], on="code", how="left")
    .merge(water_df[["code", "score_water"]], on="code", how="left")
)

# -----------------------------
# Gestion NA
# -----------------------------
climate_df["score_flood"] = climate_df["score_flood"].fillna(1)
climate_df["score_water"] = climate_df["score_water"].fillna(0)
climate_df["score_temperature"] = climate_df["score_temperature"].fillna(0)

# -----------------------------
# Sidebar poids indice
# -----------------------------
st.sidebar.header("⚙️ Paramètres de l'indice")

poids_temp = st.sidebar.slider("Poids température", 0.0, 1.0, 0.5)
poids_flood = st.sidebar.slider("Poids inondation", 0.0, 1.0, 0.1)
poids_water = st.sidebar.slider("Poids eau", 0.0, 1.0, 0.4)

st.sidebar.caption(
"""
**Poids par défaut :**
- 🌡️ Température : 0.50  
- 🌊 Inondation : 0.10  
- 💧 Eau : 0.40
"""
)

# -----------------------------
# Calcul indice
# -----------------------------
climate_df["indice_climat"] = (
    poids_temp * climate_df["score_temperature"] +
    poids_flood * climate_df["score_flood"] +
    poids_water * climate_df["score_water"]
)

# format code département
climate_df["code"] = climate_df["code"].astype(str).str.zfill(2)

# -----------------------------
# Chargement carte geojson + noms
# -----------------------------
with open("pages/tables/departements.geojson") as f:
    departements = json.load(f)

code_to_nom = {
    feature["properties"]["code"]: feature["properties"]["nom"]
    for feature in departements.get("features", [])
}
climate_df["departement"] = climate_df["code"].map(code_to_nom).fillna(climate_df["code"])
climate_df["departement_label"] = climate_df["departement"] + " (" + climate_df["code"] + ")"






#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
st.divider()

col1, col2, col3 = st.columns(3)

col1.metric(
    "Indice moyen France",
    round(climate_df["indice_climat"].mean(), 2)
)

col2.metric(
    "Meilleur département",
    climate_df.sort_values("indice_climat", ascending=False)["departement_label"].iloc[0]
)

col3.metric(
    "Moins favorable",
    climate_df.sort_values("indice_climat")["departement_label"].iloc[0]
)

st.divider()

# -----------------------------
# Création carte
# -----------------------------
color_scale = [
    (0.0, "#991b1b"),
    (0.2, "#c2410c"),
    (0.4, "#f59e0b"),
    (0.6, "#84cc16"),
    (0.8, "#22c55e"),
    (1.0, "#15803d"),
]

fig = px.choropleth(
    climate_df,
    geojson=departements,
    locations="code",
    featureidkey="properties.code",
    color="indice_climat",
    color_continuous_scale=color_scale,
    hover_name="departement_label",
    custom_data=[
        "departement",
        "code",
        "indice_climat",
        "score_temperature",
        "score_flood",
        "score_water",
    ],
)

fig.update_geos(
    fitbounds="locations",
    visible=False,
    bgcolor="rgba(0,0,0,0)",
    projection={"type": "mercator"},
)

fig.update_traces(
    marker_line_color="rgba(255,255,255,0.35)",
    marker_line_width=0.8,
    hovertemplate=(
        "<b>%{customdata[0]} (%{customdata[1]})</b><br>"
        "Indice climat: <b>%{customdata[2]:.2f}</b><br>"
        "Température: %{customdata[3]:.2f}<br>"
        "Inondation: %{customdata[4]:.2f}<br>"
        "Pression eau: %{customdata[5]:.2f}"
        "<extra></extra>"
    ),
)

fig.update_layout(
    height=650,
    margin=dict(r=0, t=0, l=0, b=0),
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    coloraxis_colorbar={
        "title": {"text": "Indice climat", "font": {"color": "#e8edf2"}},
        "tickfont": {"color": "#cfd6df"},
        "tickformat": ".2f",
        "ticks": "outside",
        "len": 0.75,
        "thickness": 14,
        "outlinewidth": 0,
        "bgcolor": "rgba(0,0,0,0)",
    },
    hoverlabel={
        "bgcolor": "#0f172a",
        "font_color": "#f8fafc",
        "bordercolor": "rgba(255,255,255,0.15)",
    },
)

# -----------------------------
# Affichage carte
# -----------------------------
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Top départements
# -----------------------------
st.subheader("🏆 Top 10 départements (conditions climatiques)")

top = climate_df.sort_values("indice_climat", ascending=False).head(10)

st.dataframe(top[["departement", "code", "indice_climat"]])

# -----------------------------
# Radar par département
# -----------------------------
st.subheader("🎯 Profil climatique par département (Radar)")

departement_selection = st.selectbox(
    "Choisis un département",
    climate_df["departement_label"].sort_values().unique(),
)

detail = climate_df.loc[
    climate_df["departement_label"] == departement_selection
].iloc[0]

radar_labels = ["Température", "Inondation", "Pression eau"]
radar_values = [
    detail["score_temperature"],
    detail["score_flood"],
    detail["score_water"],
]
max_values = [
    climate_df["score_temperature"].max(),
    climate_df["score_flood"].max(),
    climate_df["score_water"].max(),
]
radar_labels_closed = radar_labels + [radar_labels[0]]
radar_values_closed = radar_values + [radar_values[0]]
max_values_closed = max_values + [max_values[0]]
radar_max = max(radar_values + max_values)
radar_range = [0, 1] if radar_max <= 1 else [0, radar_max * 1.05]

fig_radar = go.Figure()
fig_radar.add_trace(
    go.Scatterpolar(
        r=radar_values_closed,
        theta=radar_labels_closed,
        fill="toself",
        name=departement_selection,
        line={"color": "#22c55e"},
        fillcolor="rgba(34,197,94,0.25)",
    )
)
fig_radar.add_trace(
    go.Scatterpolar(
        r=max_values_closed,
        theta=radar_labels_closed,
        name="Max national",
        mode="lines+markers",
        line={"color": "#f59e0b", "width": 2, "dash": "dash"},
        marker={"size": 6},
        hovertemplate="Max national<br>%{theta}: %{r:.2f}<extra></extra>",
    )
)

fig_radar.update_layout(
    template="plotly_dark",
    height=420,
    margin=dict(l=20, r=20, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#e8edf2"},
    polar={
        "radialaxis": {"visible": True, "range": radar_range},
        "bgcolor": "rgba(0,0,0,0)",
    },
    showlegend=True,
    legend={
        "orientation": "h",
        "y": 1.08,
        "x": 0.0,
        "font": {"color": "#cfd6df"},
    },
)

st.plotly_chart(fig_radar, use_container_width=True)


#*********************
#*********************


# un classement complet interactif
st.subheader("📊 Classement des départements")

search = st.text_input("Rechercher un département (nom ou code)")

table = climate_df.sort_values("indice_climat", ascending=False)

if search:
    search_lower = search.lower()
    table = table[
        table["code"].str.contains(search, na=False)
        | table["departement"].str.lower().str.contains(search_lower, na=False)
    ]

st.dataframe(table[["departement", "code", "indice_climat"]])


# distribution nationale
fig_hist = px.histogram(
    climate_df,
    x="indice_climat",
    nbins=30,
    title="Distribution nationale de l'indice climatique"
)

st.plotly_chart(fig_hist, use_container_width=True)
