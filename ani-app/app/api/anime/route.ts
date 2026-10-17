import { NextResponse } from 'next/server';
import { getMongoClient } from '../../../lib/mongo';
export async function GET() {
  try {
    // 1. Get the cached connection
    const client = await getMongoClient();

    // 2. Use the connection to access your DB and Collection
    const db = client.db('anime');
    const collection = db.collection('anime_anilist');

    // 3. Define and use the projection
    const projection = {
        _id: 1,
        anilist_id: 1,
        'title.english': 1,
        genres: 1,
        description: 1,
        umap_2d: 1,
        'coverImage.large': 1,
        popularity: 1
    };
    
    // 4. Run your query
    const animeData = await collection.find({}, { projection }).toArray();
    
    return NextResponse.json(animeData);

  } catch (error) {
    console.error('Failed to fetch anime data:', error);
    return NextResponse.json({ message: 'Error fetching data', error: (error as Error).message }, { status: 500 });
  }
  // NOTE: We DO NOT call client.close() here. The connection is persistent.
}