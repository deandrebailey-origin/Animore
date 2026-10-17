// This API route is responsible for hydrating anime data from MongoDB based on a list of MAL IDs.
// basically it takes a list of IDs and returns the full anime data for those IDs in one go, which is more efficient than multiple round-trips.

import { NextResponse } from 'next/server';
import { getMongoClient } from '../../../../lib/mongo';

export async function POST(request: Request) {
  try {
    const { ids } = await request.json();

    // 1. Await your pre-existing connection
    const client = await getMongoClient();
    const db = client.db('anime');

    // 2. Hydrate: Fetch all matches in one single trip to the database
    const hydratedAnime = await db.collection('anime_anilist').find({
      mal_id: { $in: ids }
    }).toArray();

    return NextResponse.json(hydratedAnime);

  } catch (error) {
    console.error("Hydration Error:", error);
    return NextResponse.json({ error: "Failed to fetch from MongoDB" }, { status: 500 });
  }
}