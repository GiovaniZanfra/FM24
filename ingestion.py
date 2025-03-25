import json
import psycopg2
import sys

# Define static keys that we don't consider part of the dynamic position scores.
STATIC_KEYS = {"Age", "Club", "Transfer Value", "Wage"}

def populate_db(json_path, save_id, conn_params):
    # Load JSON data from file
    with open(json_path, 'r') as f:
        data = json.load(f)["data"]

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    for record in data:
        name = record.get("Name")
        # Check if the player already exists (assuming name is unique)
        cur.execute("SELECT player_id FROM players WHERE name = %s", (name,))
        res = cur.fetchone()
        if res:
            player_id = res[0]
        else:
            height = _parse_height(record.get("Height"))
            cur.execute(
                "INSERT INTO players (name, nationality, height) VALUES (%s, %s, %s) RETURNING player_id",
                (name, record.get("Nat"), height)
            )
            player_id = cur.fetchone()[0]
            conn.commit()

        # Prepare the dynamic positions data as a dictionary
        positions = {k: record[k] for k in record 
                     if k not in STATIC_KEYS and isinstance(record[k], (int, float))}

        # Insert the player's snapshot into player_evolution.
        # This assumes that player_evolution has a JSONB column "positions" to store all position scores.
        cur.execute(
            """
            INSERT INTO player_evolution (player_id, save_id, age, transfer_value, wage, positions)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (player_id,
             save_id,
             record.get("Age"),
             record.get("Transfer Value"),
             record.get("Wage"),
             json.dumps(positions))
        )
        conn.commit()

    cur.close()
    conn.close()

def _parse_height(height: str) -> int:
    """Extracts the numeric height from a string like '180 cm'."""
    return int(height.split()[0]) if height else None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <path_to_json> <save_id>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    save_id = int(sys.argv[2])
    
    # Set your connection parameters here
    conn_params = {
        'dbname': 'fm24',
        'user': 'giovani',
        'password': 'giovani',
        'host': 'localhost'
    }
    
    populate_db(json_path, save_id, conn_params)
