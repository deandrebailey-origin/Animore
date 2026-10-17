import { MongoClient } from "mongodb";

// Cache the connection on globalThis so hot reloads in dev
// and repeated requests in production reuse one connection.
const globalForMongo = globalThis as typeof globalThis & {
  _mongoClientPromise?: Promise<MongoClient>;
};

export function getMongoClient(): Promise<MongoClient> {
  if (!globalForMongo._mongoClientPromise) {
    const uri = process.env.MONGODB_URI;
    if (!uri) {
      throw new Error("Please define the MONGODB_URI environment variable");
    }
    globalForMongo._mongoClientPromise = new MongoClient(uri)
      .connect()
      .catch((err) => {
        // Don't cache a failed connection; let the next request retry.
        globalForMongo._mongoClientPromise = undefined;
        throw err;
      });
  }
  return globalForMongo._mongoClientPromise;
}