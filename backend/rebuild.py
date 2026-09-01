import os
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

TABLES = {
    "country": "member_country",
    "roads": "nc_roads",
    "rail": "nc_railways",
    "ports": "ports",
    "borders": "border_posts",
    "depots": "pipeline_depot",
    "weighbridges": "weighbridge",
    "capitals": "capital_city",
}

def fetch_layer(cur, table_name):
    cur.execute(f"""
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                    'properties', to_jsonb(t) - 'geom' - 'gid'
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
            for key, table in TABLES.items():
                print(f"Fetching {table}...")
                output[key] = fetch_layer(cur, table)
    finally:
        conn.close()

    out_path = os.path.join("..", "corridor_data.json")
    with open(out_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Wrote {out_path} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()