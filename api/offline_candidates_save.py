import os
from dotenv import load_dotenv
load_dotenv()
from pymongo import UpdateOne
import numpy as np
import pandas as pd
import sklearn
import warnings
from pymongo import MongoClient
from flask import Flask, request, jsonify
from flask_cors import CORS 
warnings.simplefilter(action='ignore', category=FutureWarning)

uri = os.environ["MONGODB_URI"]
client = MongoClient(uri)
db = client.get_database('anime')

# DATABASE
anime_docs = list(db.anime_anilist.find({}, {'_id': 0}))

# taken from the csv file (too large for mongo)
ratings = pd.read_csv('user-filtered.csv', nrows=1000000)
animes = pd.DataFrame(anime_docs)

if 'mal_id' in animes.columns:
    animes = animes.rename(columns={'mal_id': 'anime_id'})

n_ratings = len(ratings)
n_movies = len(ratings['anime_id'].unique())
n_users = len(ratings['user_id'].unique())

def extract_title(title_obj):
    if isinstance(title_obj, dict):
        # Try our preferred keys first
        title = title_obj.get('english') or title_obj.get('romaji') or title_obj.get('English')
        if title:
            return title
        
        # If those fail, just grab the very first string inside the object!
        for key, value in title_obj.items():
            if isinstance(value, str) and value.strip() != "":
                return value
                
    # If it's not a dictionary at all, just stringify it
    return str(title_obj)

if 'title' in animes.columns:
    animes['Name'] = animes['title'].apply(extract_title) #add the Names column for pandas
else:
    animes['Name'] = "Unknown Title"

from scipy.sparse import csr_matrix

def create_matrix(df):
    
    N = len(df['user_id'].unique())
    M = len(df['anime_id'].unique())
 
    user_mapper = dict(zip(np.unique(df["user_id"]), list(range(N))))
    anime_mapper = dict(zip(np.unique(df["anime_id"]), list(range(M))))
 
    user_inv_mapper = dict(zip(list(range(N)), np.unique(df["user_id"])))
    anime_inv_mapper = dict(zip(list(range(M)), np.unique(df["anime_id"])))
    
    user_index = [user_mapper[i] for i in df['user_id']]
    anime_index = [anime_mapper[i] for i in df['anime_id']]

    X = csr_matrix((df["rating"], (anime_index, user_index)), shape=(M, N))
    
    return X, user_mapper, anime_mapper, user_inv_mapper, anime_inv_mapper
    
X, user_mapper, anime_mapper, user_inv_mapper, anime_inv_mapper = create_matrix(ratings)

from sklearn.neighbors import NearestNeighbors

def find_similar_animes(movie_id, X, k, metric='cosine', show_distance=False):
    neighbour_ids = []
    
    if movie_id not in anime_mapper:
        print(f"Movie ID {movie_id} not found in movie_mapper!")
        return []

    anime_ind = anime_mapper[movie_id]
    anime_vec = X[anime_ind]
    k += 1  
    kNN = NearestNeighbors(n_neighbors=k, algorithm="brute", metric=metric)
    kNN.fit(X)
    anime_vec = anime_vec.reshape(1, -1)
    neighbour = kNN.kneighbors(anime_vec, return_distance=show_distance)
    
    for i in range(0, k):
        n = neighbour.item(i)
        neighbour_ids.append(anime_inv_mapper[n])
    
    neighbour_ids.pop(0) 
    return neighbour_ids

# RECOMMENDATION FUNCTIONS (First one not necessary right now need to be changed to recommend based on anime_id input)
def recommend_animes_for_user(user_id, X, user_mapper, anime_mapper, anime_inv_mapper, k=10):
    df1 = ratings[ratings['user_id'] == user_id]

    anime_id = df1[df1['rating'] == max(df1['rating'])]['anime_id'].iloc[0]

    anime_titles = dict(zip(animes['anime_id'], animes['Name']))

    similar_ids = find_similar_animes(anime_id, X, k)

    print(f"Since you watched {anime_titles[anime_id]}, you might also like:")

    for i in similar_ids:
        if i in anime_titles:
            print(anime_titles[i])

def recommend_animes_for_anime(anime_id, X, user_mapper, movie_mapper, movie_inv_mapper, k=10):

    movie_id = anime_id

    anime_titles = dict(zip(animes['anime_id'], animes['Name']))

    similar_ids = find_similar_animes(movie_id, X, k)

    print(f"Since you watched {anime_titles[movie_id]}, you might also like:")

    #simply print titles of recommended animes
    for i in similar_ids:
        if i in anime_titles:
            print(anime_titles[i])

    #returns full details of recommended animes
    recommended = animes[animes['anime_id'].isin(similar_ids)].to_dict(orient="records")

    return recommended

user_id = 558 
#recommend_animes_for_user(user_id, X, user_mapper, movie_mapper, movie_inv_mapper, k=10)
#recommend_animes_for_anime(170, X, user_mapper, movie_mapper, movie_inv_mapper, k=10)

unique_anime_ids = ratings['anime_id'].unique()
batch_size = 1000
bulk_operations = []

for anime_id in unique_anime_ids:
    candidates = find_similar_animes(anime_id, X, k=50)  # Get top 10 similar animes
    safe_candidates = [int(x) for x in candidates]
    safe_id = int(anime_id)
    bulk_operations.append(
        UpdateOne(
            {"mal_id": safe_id},
            {"$set": {"collab_candidates": safe_candidates}}

        )
    )

    if len(bulk_operations) >= batch_size:
        db.anime_anilist.bulk_write(bulk_operations)
        print(f"Updated {len(bulk_operations)} documents with collaborative filtering candidates.")
        bulk_operations = [] # clear for next batch

    if len(bulk_operations) > 0:
        db.anime_anilist.bulk_write(bulk_operations)
        print(f"Updated {len(bulk_operations)} documents with collaborative filtering candidates.")

print("All documents updated with collaborative filtering candidates.")







db.anime_anilist.bulk_write(bulk_operations)
print(f"Updated {len(bulk_operations)} documents with collaborative filtering candidates.")