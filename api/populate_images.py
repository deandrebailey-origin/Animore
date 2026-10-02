import os
import time
import requests
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
MONGODB_URI = os.environ["MONGODB_URI"]
DB_NAME = "anime"
COLLECTION_NAME = "anime_anilist"
ANILIST_API_URL = "https://graphql.anilist.co"
BATCH_SIZE = 50  # Process 50 anime per API call

def build_batch_query(anime_batch):
    """Dynamically creates a GraphQL query for a batch of anime."""
    query_parts = []
    variables = {}
    
    # Using aliases in GraphQL to ask for multiple items in one query
    for i, anime in enumerate(anime_batch):
        anilist_id = anime.get("anilist_id")
        if anilist_id:
            # e.g., anime_0: Media(id: $id_0) { ... }
            query_parts.append(f"""
                anime_{i}: Media(id: $id_{i}, type: ANIME) {{
                    id
                    coverImage {{
                        large
                    }}
                }}
            """)
            variables[f"id_{i}"] = anilist_id
    
    # Combine all parts into a single query string
    full_query = f"query ({', '.join([f'${key}: Int' for key in variables])}) {{{' '.join(query_parts)}}}"
    return full_query, variables

def main():
    if not MONGODB_URI:
        raise Exception("Please define the MONGODB_URI environment variable")

    client = MongoClient(MONGODB_URI)
    print("🚀 Starting batch image population script...")

    try:
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print("✅ Connected to MongoDB")

        animes_to_update = list(collection.find({"coverImage": {"$exists": False}}))

        if not animes_to_update:
            print("✅ No anime need updating.")
            return

        total_anime = len(animes_to_update)
        print(f"Found {total_anime} anime to update...")

        # Process the anime in batches
        for i in range(0, total_anime, BATCH_SIZE):
            batch = animes_to_update[i:i + BATCH_SIZE]
            print(f"\n--- Processing batch {i//BATCH_SIZE + 1} ({len(batch)} anime) ---")

            batch_query, batch_variables = build_batch_query(batch)
            
            if not batch_variables:
                print("   ⚠️ Batch is empty or contains no valid anilist_ids. Skipping.")
                continue

            try:
                response = requests.post(
                    ANILIST_API_URL,
                    json={"query": batch_query, "variables": batch_variables}
                )
                response.raise_for_status()
                
                api_data = response.json().get("data", {})
                
                # Prepare a list of update operations for MongoDB
                update_operations = []
                for idx, anime_doc in enumerate(batch):
                    result_key = f"anime_{idx}"
                    media_data = api_data.get(result_key)
                    
                    if media_data and media_data.get("coverImage") and media_data["coverImage"].get("large"):
                        image_url = media_data["coverImage"]["large"]
                        update_operations.append(
                            UpdateOne(
                                {"_id": anime_doc["_id"]},
                                {"$set": {"coverImage": {"large": image_url}}}
                            )
                        )
                        print(f"   ✅ Found image for anilist_id: {anime_doc['anilist_id']}")
                    else:
                        print(f"   ⚠️ Image not found for anilist_id: {anime_doc['anilist_id']}")

                # Perform the bulk update to the database if there are any operations
                if update_operations:
                    print(f"   Writing {len(update_operations)} updates to the database...")
                    collection.bulk_write(update_operations)
                else:
                    print("   No images found in this batch to update.")

            except Exception as e:
                print(f"   ❌ Failed to process batch. Error: {e}")

            # Pause between batches to respect the rate limit
            print(f"--- Batch complete. Pausing for 1 second... ---")
            time.sleep(1.5)

    finally:
        client.close()
        print("\n✅ MongoDB connection closed. Script finished.")

if __name__ == "__main__":
    main()