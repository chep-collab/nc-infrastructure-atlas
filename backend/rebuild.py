import os
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    host = os.getenv("PGHOST", "192.168.48.18")
    port = os.getenv("PGPORT", "7456")
    dbname = os.getenv("PGDATABASE", "ncto_staging")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD")
    if not password:
        raise SystemExit("PGPASSWORD is not set. Put it in backend/.env")
    print(f"Connecting to {user}@{host}:{port}/{dbname}")
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )

# Each entry: output_key -> (table_name, {property_name_the_map_expects: actual_db_column})
LAYERS = {
    "country": ("member_country", {
        "ADM0_EN": "adm0_en",
        "ADM0_PCODE": "adm0_pcode",
        "ADM0_REF": "adm0_ref",
        "CNTRY_NAME": "cntry_name",
    }),
    "roads": ("nc_roads", {
        "NAME": "name",
        "COUNTRY": "country",
        "STATUS": "status",
        "DISTA_KM": "dista_km",
    }),
    "rail": ("nc_railways", {
        "Country": "country",
        "RailType": "railtype",
        "RailName": "railname",
        "RailOrign": "railorign",
        "RailDest": "raildest",
        "Length_KM": "length_km",
        "Remarks": "remarks",
    }),
    "ports": ("ports", {
        "NAME": "name",
        "COUNTRY": "country",
        "CATEGORY": "category",
        "SECTION_NA": "section_na",
        "Printing": "printing",
    }),
    "borders": ("border_posts", {
        "Country Pa": "country pa",
        "Border Pos": "border pos",
        "OSBP Statu": "osbp statu",
        "Type[1]": "type[1]",
        "Category": "category",
    }),
    "depots": ("pipeline_depot", {
        "NAME": "name",
    }),
    "weighbridges": ("weighbridge", {
        "NAME": "name",
        "COUNTRY": "country",
        "SECTION_NA": "section_na",
        "WBName": "wbname",
    }),
    "capitals": ("capital_city", {
        "ADM_1": "adm_1",
        "ADM_2": "adm_2",
        "COUNTRY": "country",
        "STATUS": "status",
        "TRANSIT_TO": "transit_to",
    }),
    "pipeline": ("pipeline_wayleave", {
        "shape_area": "shape_area",
        "Length": "length_km_"
    }),
}

def build_properties_sql(prop_map):
    # Builds: jsonb_build_object('PropName', "db column", ...)
    parts = []
    for prop_name, db_col in prop_map.items():
        prop_escaped = prop_name.replace("'", "''")
        col_escaped = db_col.replace('"', '""')
        parts.append(f"'{prop_escaped}', \"{col_escaped}\"")
    return "jsonb_build_object(" + ", ".join(parts) + ")"

def fetch_layer(cur, table_name, prop_map):
    props_sql = build_properties_sql(prop_map)
    cur.execute(f"""
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                    'properties', {props_sql}
                )
            ), '[]'::jsonb)
        ) AS fc
        FROM {table_name} t;
    """)
    return cur.fetchone()["fc"]

def main():
    conn = get_connection()
    output = {}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for key, (table, prop_map) in LAYERS.items():
                print(f"Fetching {table}...")
                output[key] = fetch_layer(cur, table, prop_map)
    finally:
        conn.close()

    out_path = os.path.join("..", "corridor_data.json")
    with open(out_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Wrote {out_path} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()