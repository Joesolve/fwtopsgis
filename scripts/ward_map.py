import geopandas as gpd
import folium
from pathlib import Path

# ---------- PATHS ----------
base_dir = Path("..")  # from scripts/ folder, go up one level
data_dir = base_dir / "data"
shp_path = data_dir / "FWT_WARDPOP.shp"

# ---------- LOAD SHAPEFILE ----------
gdf = gpd.read_file(shp_path)

print("Columns:", gdf.columns)
print("CRS:", gdf.crs)

# Clean copy
gdf_clean = gdf.copy()

# Make sure Ward_No is numeric
gdf_clean["Ward_No"] = gdf_clean["Ward_No"].astype(int)

# Rename population column if present
if "SUM_Final_" in gdf_clean.columns:
    gdf_clean = gdf_clean.rename(columns={"SUM_Final_": "Population"})
else:
    gdf_clean["Population"] = None  # fallback if not there

# ---------- DEFINE BLOCK 6 ----------
# Assumption: Block 6 = wards 429–434
block6_wards = [429, 430, 431, 432, 433, 434]

block6_gdf = gdf_clean[gdf_clean["Ward_No"].isin(block6_wards)].copy()
other_gdf  = gdf_clean[~gdf_clean["Ward_No"].isin(block6_wards)].copy()

print("Block 6 wards present:", sorted(block6_gdf["Ward_No"].unique()))

# ---------- ENSURE WGS84 ----------
if gdf_clean.crs is None or gdf_clean.crs.to_epsg() != 4326:
    gdf_clean = gdf_clean.to_crs(epsg=4326)
    block6_gdf = block6_gdf.to_crs(epsg=4326)
    other_gdf  = other_gdf.to_crs(epsg=4326)

# ---------- BASE MAP CENTER ----------
center = block6_gdf.geometry.unary_union.centroid
center_lat, center_lon = center.y, center.x

m = folium.Map(location=[center_lat, center_lon],
               zoom_start=14,
               tiles="OpenStreetMap")

# ---------- LAYER 1: ALL OTHER WARDS (CONTEXT) ----------
def style_other(feature):
    return {
        "fillColor": "#dddddd",
        "color": "#888888",
        "weight": 0.8,
        "fillOpacity": 0.4,
    }

folium.GeoJson(
    other_gdf.to_json(),
    name="Other Wards",
    style_function=style_other,
    tooltip=folium.GeoJsonTooltip(
        fields=["Ward_No"],
        aliases=["Ward:"],
    ),
).add_to(m)

# ---------- LAYER 2: BLOCK 6 WARDS (HIGHLIGHT) ----------
def style_block6(feature):
    return {
        "fillColor": "#ffcc00",  # strong yellow
        "color": "#ff6600",      # strong border
        "weight": 2.5,
        "fillOpacity": 0.7,
    }

block6_layer = folium.GeoJson(
    block6_gdf.to_json(),
    name="Block 6 (Wards 429–434)",
    style_function=style_block6,
    tooltip=folium.GeoJsonTooltip(
        fields=["Ward_No", "Population"],
        aliases=["Ward:", "Population:"],
        localize=True
    ),
    highlight_function=lambda x: {"weight": 3, "color": "red"},
).add_to(m)

# ---------- LABELS: WARD NUMBERS FOR BLOCK 6 ----------
for _, row in block6_gdf.iterrows():
    centroid = row.geometry.centroid
    folium.map.Marker(
        [centroid.y, centroid.x],
        icon=folium.DivIcon(
            html=f"""
            <div style="font-size: 12px; font-weight: bold; color: #000;
                        background: rgba(255,255,255,0.7);
                        padding: 2px 4px; border-radius: 3px;">
                {int(row['Ward_No'])}
            </div>
            """
        )
    ).add_to(m)

folium.LayerControl().add_to(m)

# ---------- SAVE MAP ----------
map_path = base_dir / "block6_boundary_map.html"
m.save(map_path)
print(f"Map saved as: {map_path}")

# ---------- EXPORT BLOCK 6 ONLY AS FILES ----------
# 1) GeoJSON (easy to share)
block6_geojson = base_dir / "block6_wards.geojson"
block6_gdf.to_file(block6_geojson, driver="GeoJSON")
print(f"Block 6 GeoJSON saved as: {block6_geojson}")

# 2) Shapefile (for GIS tools)
block6_shp_dir = base_dir / "block6_shapefile"
block6_shp_dir.mkdir(exist_ok=True)
block6_gdf.to_file(block6_shp_dir / "block6_wards.shp")
print(f"Block 6 Shapefile saved in folder: {block6_shp_dir}")
