"use client";

import { useState, useEffect, useRef } from "react";
import * as d3 from 'd3';
import SiteHeader from "../../components/SiteHeader";
import "../globals.css";

// Interface remains the same
interface Anime {
    _id: string;
    anilist_id: number;
    title: {
        english: string;
    };
    genres: string[];
    description: string;
    umap_2d: [number, number];
    coverImage?: {
        large: string;
    };
    popularity: number;
}

interface TooltipData {
    visible: boolean;
    content: Anime | null;
    x: number;
    y: number;
}

export default function AnimeMapPage() {
    const svgRef = useRef<SVGSVGElement | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [tooltip, setTooltip] = useState<TooltipData>({ visible: false, content: null, x: 0, y: 0 });

    // --- STATE FOR FILTERING ---
    const [allAnimeData, setAllAnimeData] = useState<Anime[]>([]);
    const [animeData, setAnimeData] = useState<Anime[]>([]);
    const [availableGenres, setAvailableGenres] = useState<string[]>([]);
    const [selectedGenres, setSelectedGenres] = useState<Set<string>>(new Set());
    const [popularityBounds, setPopularityBounds] = useState({ min: 0, max: 1 });
    const [minPopularity, setMinPopularity] = useState(0); 
    const [searchTerm, setSearchTerm] = useState(""); // <-- NEW: State for search bar


    // Effect to fetch initial data
    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('/api/anime');
                if (!response.ok) throw new Error('Failed to fetch data');
                const rawData: Anime[] = await response.json();

                const validData = rawData.filter(anime => 
                    anime.umap_2d && Array.isArray(anime.umap_2d) && anime.umap_2d.length === 2 && typeof anime.popularity === 'number' && anime.title.english
                );
                
                if (validData.length === 0 && rawData.length > 0) {
                    console.warn("Warning: All fetched data was filtered out. Check 'umap_2d' and 'popularity' fields.");
                }

                setAllAnimeData(validData);

                const allGenres = new Set(validData.flatMap(a => a.genres));
                setAvailableGenres(Array.from(allGenres).sort());

                const popExtent = d3.extent(validData, d => d.popularity) as [number, number] | [undefined, undefined];
                if (popExtent[0] !== undefined && popExtent[1] !== undefined) {
                    setPopularityBounds({ min: popExtent[0], max: popExtent[1] });
                    // --- MODIFIED: Set initial popularity to 50000 ---
                    // It's clamped to ensure it doesn't exceed the max popularity
                    setMinPopularity(Math.min(50000, popExtent[1])); 
                }
            } catch (error) {
                console.error(error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);


    // Effect for applying ALL filters (including search)
    useEffect(() => {
        let dataToFilter = [...allAnimeData];

        // 1. Apply search term filter
        if (searchTerm) {
            dataToFilter = dataToFilter.filter(anime =>
                anime.title.english.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }
        
        // 2. Apply genre filter
        if (selectedGenres.size > 0) {
            dataToFilter = dataToFilter.filter(anime =>
                anime.genres.some(genre => selectedGenres.has(genre))
            );
        }

        // 3. Apply popularity filter
        dataToFilter = dataToFilter.filter(anime => anime.popularity >= minPopularity);

        setAnimeData(dataToFilter);

    }, [searchTerm, selectedGenres, minPopularity, allAnimeData]); // <-- MODIFIED: Added searchTerm dependency


    // Effect to draw/update the D3 chart
    useEffect(() => {
      // ... (This entire useEffect block remains unchanged)
        if (isLoading || !svgRef.current) return;
        
        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();

        if (animeData.length === 0) {
            svg.append("text")
                .attr("x", "50%")
                .attr("y", "50%")
                .attr("text-anchor", "middle")
                .attr("fill", "white")
                .attr("font-size", "20px")
                .text("No results match your filters.");
            return;
        }

        const { width, height } = svg.node()!.getBoundingClientRect();
        const margin = { top: 20, right: 20, bottom: 20, left: 20 };
        
        const xExtent = d3.extent(animeData, d => d.umap_2d[0]) as [number, number];
        const yExtent = d3.extent(animeData, d => d.umap_2d[1]) as [number, number];
        const popularityExtent = d3.extent(animeData, d => d.popularity) as [number, number];
        
        const xScale = d3.scaleLinear().domain([xExtent[0] - 1, xExtent[1] + 1]).range([margin.left, width - margin.right]);
        const yScale = d3.scaleLinear().domain([yExtent[0] - 1, yExtent[1] + 1]).range([height - margin.bottom, margin.top]);
        const radiusScale = d3.scaleSqrt().domain(popularityExtent).range([3, 15]);

        const g = svg.append("g").attr("class", "points-group");

        g.selectAll("circle")
            .data(animeData)
            .join("circle")
            .attr("cx", d => xScale(d.umap_2d[0]))
            .attr("cy", d => yScale(d.umap_2d[1]))
            .attr("r", d => radiusScale(d.popularity))
            .attr("fill", "white")
            .attr("opacity", 0.7)
            .style("cursor", "pointer")
            .style("transition", "all 0.2s ease")
            .on("mouseover", (event, d) => {
                const currentRadius = radiusScale(d.popularity);
                d3.select(event.currentTarget as SVGCircleElement).attr("fill", "#FFC107").attr("r", currentRadius + 3).attr("opacity", 1);
                setTooltip({ visible: true, content: d, x: event.pageX, y: event.pageY });
            })
            .on("mouseout", (event, d) => {
                d3.select(event.currentTarget as SVGCircleElement).attr("fill", "white").attr("r", radiusScale(d.popularity));
                setTooltip({ visible: false, content: null, x: 0, y: 0 });
            });

        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([1, 20])
            .on("zoom", (event) => {
                g.attr("transform", event.transform.toString());
            });

        svg.call(zoom);
    }, [animeData, isLoading]);


    // --- FILTER HANDLER FUNCTIONS ---
    const handleGenreChange = (genre: string) => {
        const newSelectedGenres = new Set(selectedGenres);
        if (newSelectedGenres.has(genre)) {
            newSelectedGenres.delete(genre);
        } else {
            newSelectedGenres.add(genre);
        }
        setSelectedGenres(newSelectedGenres);
    };

    const handlePopularityChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setMinPopularity(Number(event.target.value));
    };

    // <-- NEW: Handler for search input -->
    const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(event.target.value);
    };

    return (
        <div className="font-sans min-h-screen flex flex-col bg-black">
            <SiteHeader />
            <main className="flex-grow p-4 sm:p-8 flex flex-col md:flex-row gap-4">

                {/* --- FILTER PANEL UI --- */}
                <aside className="w-full md:w-64 lg:w-72 bg-black p-4 rounded-lg text-white flex-shrink-0 h-full overflow-y-auto">
                    <h2 className="text-xl font-bold mb-4">FILTERS</h2>

                    {/* <-- NEW: Search Bar --> */}
                    <div className="mb-6">
                        <label htmlFor="search" className="block mb-2 font-semibold">SEARCH</label>
                        <input
                            id="search"
                            type="text"
                            placeholder="Search by title..."
                            value={searchTerm}
                            onChange={handleSearchChange}
                            className="w-full bg-black border border-white px-3 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                    </div>

                    {/* Popularity Filter */}
                    <div className="mb-6">
                        <label htmlFor="popularity" className="block mb-2 font-semibold">
                            MINIMUM POPULARITY: {minPopularity.toLocaleString()}
                        </label>
                        <input
                            id="popularity"
                            type="range"
                            min={popularityBounds.min}
                            max={popularityBounds.max}
                            value={minPopularity}
                            onChange={handlePopularityChange}
                            className="w-full h-2 bg-white rounded-lg appearance-none cursor-pointer"
                        />
                    </div>

                    {/* Genre Filter */}
                    <div>
                        <h3 className="font-semibold mb-2">GENRES</h3>
                        <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
                            {availableGenres.map(genre => (
                                <div key={genre} className="flex items-center">
                                    <input
                                        type="checkbox"
                                        id={`genre-${genre}`}
                                        checked={selectedGenres.has(genre)}
                                        onChange={() => handleGenreChange(genre)}
                                        className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                    />
                                    <label htmlFor={`genre-${genre}`} className="ml-3 text-sm">
                                        {genre}
                                    </label>
                                </div>
                            ))}
                        </div>
                    </div>
                </aside>
                
                {/* --- Chart Area --- */}
                <div className="flex-grow w-full h-[calc(100vh-150px)] border border-white outline-2 shadow-lg bg-black overflow-hidden relative flex items-center justify-center">
                    {isLoading ? (<div className="text-white text-xl font-bold">LOADING MAP DATA...</div>)
                                : (<svg ref={svgRef} className="w-full h-full"></svg>)
                    }
                    {!isLoading && tooltip.visible && tooltip.content && (
                        // ... (Tooltip JSX remains unchanged)
                        <div
                            className="absolute bg-white text-black p-3 border shadow-xl w-60 pointer-events-none flex flex-col gap-2"
                            style={{ top: tooltip.y - 275, left: tooltip.x - 50}}
                        >
                            {tooltip.content.coverImage && (
                                <img
                                    src={tooltip.content.coverImage.large}
                                    alt={`Poster for ${tooltip.content.title.english}`}
                                    className="rounded-md"
                                />
                            )}
                            <div>
                                <h3 className="font-bold text-md mb-1">{tooltip.content.title.english}</h3>
                                <p className="text-xs text-gray-600">
                                    <strong>Popularity:</strong> {tooltip.content.popularity.toLocaleString()}
                                </p>
                                <p className="text-xs text-gray-600">
                                    <strong>Genres:</strong> {tooltip.content.genres.join(', ')}
                                </p>
                                <p className="text-xs text-gray-600 line-clamp-3">
                                    <strong>Description:</strong> {tooltip.content.description}
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}