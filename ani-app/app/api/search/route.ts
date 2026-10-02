import { NextResponse } from 'next/server';
import clientPromise from '../../../lib/mongo';

// Escape regex special characters so user input is matched as plain text
function escapeRegex(text: string) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('query')?.trim();

    if (!query) {
      return NextResponse.json({ message: 'Search query is required' }, { status: 400 });
    }

    const client = await clientPromise;
    const collection = client.db('anime').collection('anime_anilist');

    const searchRegex = new RegExp(`^${escapeRegex(query)}`, 'i');

    const suggestions = await collection
      .find(
        { $or: [{ 'title.english': searchRegex }, { 'title.romaji': searchRegex }] },
        { projection: { _id: 0, 'title.english': 1, 'title.romaji': 1 } }
      )
      .limit(5)
      .toArray();

    // Prefer the English title, fall back to romaji, and drop any empty results
    const titles = suggestions
      .map((s) => s.title?.english || s.title?.romaji)
      .filter(Boolean);

    return NextResponse.json(titles);
  } catch (error) {
    console.error('Search API error:', error);
    return NextResponse.json({ message: 'Error fetching search suggestions' }, { status: 500 });
  }
}