import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="flex justify-between items-center p-4 sm:p-8">
      <Link href="/" className="text-4xl font-bold flex">
        ANIMORE
        <span className="animate-blink text-amber-300">+</span>
      </Link>

      <nav className="flex gap-4">
        <Link
          href="/explore"
          className="outline-2 px-6 py-3 bg-black text-white hover:bg-white hover:text-black transition font-bold"
        >
          EXPLORE
        </Link>
        <Link
          href="/map"
          className="outline-2 px-6 py-3 bg-black text-white hover:bg-white hover:text-black transition font-bold"
        >
          MAP
        </Link>
      </nav>
    </header>
  );
}