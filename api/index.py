import os
from dotenv import load_dotenv
load_dotenv()
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

#print(ratings.head())
#print(animes.head())

# TEST AND MATRIX



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


#print(f"Number of ratings: {n_ratings}")
#print(f"Number of unique anime_id's: {n_movies}")
#print(f"Number of unique users: {n_users}")

#user_freq = ratings[['user_id','anime_id']].groupby('user_id').count().reset_index()
#user_freq.columns = ['user_id','n_ratings']
#print(user_freq.head())

#mean_rating = ratings.groupby('anime_id')[['rating']].mean()
#lowest_rated = mean_rating['rating'].idxmin()
#animes.loc[animes['anime_id'] == lowest_rated]
#highest_rated = mean_rating['rating'].idxmax()
#animes.loc[animes['anime_id'] == highest_rated]
#ratings[ratings['anime_id']==highest_rated]
#ratings[ratings['anime_id']==lowest_rated]

#movie_stats = ratings.groupby('anime_id')[['rating']].agg(['count', 'mean'])
#movie_stats.columns = movie_stats.columns.droplevel()

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


app = Flask(__name__) # Initialize Flask app listens for requests and routes them to appropriate functions
CORS(app)

# NEW function to find an anime_id from a title
def get_anime_id_from_title(title_str):
    # Case-insensitive search for the title
    result = animes[animes['Name'].str.contains(title_str, case=False, na=False)]
    if not result.empty:
        return result.iloc[0]['anime_id']
    return None

print(find_similar_animes(1, X, 5))

@app.route("/candidates", methods=["GET"])
def candidates():
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "title required"}), 400
    
    anime_id = get_anime_id_from_title(title)
    if anime_id is None:
        return jsonify({"error": f"Anime '{title}' not found"}), 404
    
    candidate_ids = find_similar_animes(anime_id, X, k=50)

    return jsonify({
        "source_id": int(anime_id),
        "candidate_ids":  [int(x) for x in candidate_ids]
    })

@app.route("/candidates_names", methods=["GET"])
def candidates_names():
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "title required"}), 400
    
    anime_id = get_anime_id_from_title(title)
    if anime_id is None:
        return jsonify({"error": f"Anime '{title}' not found"}), 404
    
    candidate_ids = find_similar_animes(anime_id, X, k=50)

    ani = animes[animes['anime_id'].isin(candidate_ids)].to_dict(orient="records")

    return jsonify({
        "animes": ani
    })

# --- Updated Flask Route ---
@app.route("/recommend", methods=["GET"])
def recommend_anime():
    title = request.args.get('title') # Get title from query parameter ?title=...
    if not title:
        return jsonify({"error": "Title parameter is required"}), 400

    anime_id = get_anime_id_from_title(title)
    if anime_id is None:
        return jsonify({"error": f"Anime '{title}' not found"}), 404

    # Get the collaborative filtering recommendations
    recs = recommend_animes_for_anime(anime_id, X, user_mapper, anime_mapper, anime_inv_mapper, k=10)
    
    # Return a clean list of recommendations with just the data we need
    response_data = []
    for rec in recs:
        response_data.append({
            '_id': rec.get('anime_id'), # Use anime_id as the primary identifier
            'title': {'english': rec.get('Name')},
            'genres': rec.get('Genres', '').split(', ')
        })

    return jsonify(response_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000, use_reloader=False)

#run python main.py to start the Flask server
#open browsert to http://127.0.0.1:5000/recommend/anime/??? where ??? is a valid anime_id to see the recommendations for that anime