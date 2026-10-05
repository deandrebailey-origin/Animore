import { MongoClient } from "mongodb";

const uri = process.env.MONGODB_URI;
const options = {};

if (!uri) {
  throw new Error("Please define the MONGODB_URI environment variable");
}

// Tell TypeScript that globalThis may hold a cached connection promise
const globalForMongo = globalThis as typeof globalThis & {
  _mongoClientPromise?: Promise<MongoClient>;
};

let clientPromise: Promise<MongoClient>;

if (process.env.NODE_ENV === "development") {
  // Reuse one connection across hot reloads in development
  if (!globalForMongo._mongoClientPromise) {
    globalForMongo._mongoClientPromise = new MongoClient(uri, options).connect();
  }
  clientPromise = globalForMongo._mongoClientPromise;
} else {
  // In production, the code isn't reloaded, so connect once normally
  clientPromise = new MongoClient(uri, options).connect();
}

export default clientPromise;