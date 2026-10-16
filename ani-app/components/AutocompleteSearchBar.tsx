"use client";

import { useState, useEffect } from 'react';

interface AutocompleteSearchBarProps {
  onSearch: (searchTerm: string) => void;
}

export default function AutocompleteSearchBar({ onSearch }: AutocompleteSearchBarProps) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // This useEffect handles fetching suggestions as the user types
  useEffect(() => {
    // Don't search if the query is too short
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }


    // Debounce: Wait 300ms after the user stops typing to fetch
    const debounceTimer = setTimeout(() => {
      fetch(`/api/search?query=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          setSuggestions(data);
        })
        .catch(console.error)
    }, 300);

    // Cleanup: Clear the timer if the user types again
    return () => clearTimeout(debounceTimer);
  }, [query]); // This effect re-runs whenever the 'query' changes

  const handleSelectSuggestion = (suggestion: string) => {
    setQuery(suggestion);
    setSuggestions([]);
    onSearch(suggestion);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSuggestions([]);
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-lg relative">
      <input
        type="search"
        name="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter an anime title (e.g., Cowboy Bebop)"
        className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
        autoComplete="off"
      />
      {/* Suggestions Dropdown */}
      {suggestions.length > 0 && (
        <ul className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-lg">
          {suggestions.map((suggestion, index) => (
            <li
              key={index}
              onClick={() => handleSelectSuggestion(suggestion)}
              className="px-4 py-2 cursor-pointer hover:bg-gray-700"
            >
              {suggestion}
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}