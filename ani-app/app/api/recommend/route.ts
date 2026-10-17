import { NextResponse } from 'next/server';
import { getMongoClient } from '../../../lib/mongo';
import { escapeRegex } from '../../../lib/escapeRegex';

export async function GET(request: Request) {
  try {
    // 1. Get the search title from the request URL
    const { searchParams } = new URL(request.url);
    const title = searchParams.get('title');

    if (!title) {
      return NextResponse.json({ message: 'Anime title is required' }, { status: 400 });
    }

    // 2. Connect to the database
    const client = await getMongoClient();
    const db = client.db('anime');
    const collection = db.collection('anime_anilist');

    // 3. Find the source anime to get its embedding vector
    const searchRegex = new RegExp(escapeRegex(title), 'i');
    const sourceAnime = await collection.findOne({ 'title.english': { $regex: searchRegex } });
    
    if (!sourceAnime || !sourceAnime.embedding) {
      return NextResponse.json({ message: `Could not find an entry for '${title}'` }, { status: 404 });
    }

    const sourceEmbedding = sourceAnime.embedding;

    // 4. Define and run the vector search pipeline
    const pipeline = [
      {
        '$vectorSearch': {
          index: 'vector_index',
          path: 'embedding',
          queryVector: sourceEmbedding,
          numCandidates: 100,
          limit: 10,
          filter: {
            _id: { $ne: sourceAnime._id } // Exclude the source anime itself
          }
        }
      },
      {
        '$project': { // Only return the fields we need
          _id: 1,
          'title.english': 1,
          genres: 1,
          'coverImage.large': 1,
          popularity: 1,
          score: { '$meta': 'vectorSearchScore' }
        }
      }
    ];

    const recommendations = await collection.aggregate(pipeline).toArray();

    // 5. Return the results
    return NextResponse.json(recommendations);

  } catch (error) {
    console.error('Recommendation API error:', error);
    return NextResponse.json({ message: 'Error fetching recommendations' }, { status: 500 });
  }
}