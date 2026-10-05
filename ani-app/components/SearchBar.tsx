'use client';

import { useState, FormEvent, useEffect } from "react";

interface Item {
  _id: string;
  Name: string;
  anime_id: number;
}

interface Recommendation {
  anime_id: number;
  Name: string;
  Genre?: string;
  Episodes?: number;
  Rating?: number;
}

export default function SearchBar() {
  const [query, setQuery] = useState<string>("");
  const [results, setResults] = useState<Item[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Debounced search effect
  useEffect(() => {
    if (query.trim().length === 0) {
      setResults([]);
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data: Item[] = await res.json();
        setResults(data.splice(0, 20)); // Limit to top 20 results
      } catch (error) {
        console.error("Search error:", error);
      } finally {
        setIsLoading(false);
      }
    }, 300); // 300ms delay

    return () => clearTimeout(delayDebounceFn);
  }, [query]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); // Prevent form submission
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="RECOMMENDATIONS FROM..."
          className="outline-2 p-2 pl-2 w-full m-2"
          autoComplete="off"
        />
      </form>

      {/* Search results */}
      {(results.length > 0 || isLoading) && (
        <div className="mt-4 p-4 rounded-lg">
          <h3 className="font-bold text-white mb-2">Search Results:</h3>

          {isLoading ? (
            <p className="text-black">Loading...</p>
          ) : (
            <ul>
              {results.map((item) => (
                <li key={item._id} className="p-2 text-white">
                  <button
                    className="w-full p-3 text-left hover:bg-gray-800 transition cursor-pointer text-white"
                    onClick={async () => {
                      try {
                        const res = await fetch(
                          `http://127.0.0.1:5000/recommend/anime/${item.anime_id}`
                        );
                        const data = await res.json();
                        setRecommendations(data.recommendations || []);
                      } catch (error) {
                        console.error("Recommendation fetch error:", error);
                      }
                    }}
                  >
                    {item.Name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="mt-6 p-4 rounded-lg bg-gray-900">
          <h3 className="font-bold text-white mb-2">Recommendations:</h3>
          <ul>
            {recommendations.map((anime, index) => (
              <li
                key={index}
                className="p-3 border-b border-gray-700 text-white"
              >
                <h4 className="font-semibold">{anime.Name}</h4>
                {anime.Genre && <p>Genre: {anime.Genre}</p>}
                {anime.Episodes && <p>Episodes: {anime.Episodes}</p>}
                {anime.Rating && <p>Rating: {anime.Rating}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* No results found */}
      {results.length === 0 && query && !isLoading && (
        <div className="mt-4 p-4 rounded-lg">
          <p className="text-black">No results found for &ldquo;{query}&rdquo;</p>
        </div>
      )}
    </div>
  );
}
