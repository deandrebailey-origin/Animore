import os
from dotenv import load_dotenv
load_dotenv()
# PCA -> UMAP Visualization
# -------------------------
# PCA is a linear dimensionality reduction technique that projects data onto orthogonal axes of maximum variance.
# it finds directions (principal components) that capture the most variance in the data.
# reducing dimensions while preserving as much information as possible and distances between points.
# UMAP is a non-linear dimensionality reduction technique that preserves both local and global structure in the data.
# UMAP constructs a high-dimensional graph representation of the data and optimizes a low-dimensional layout to preserve the graph's structure.
# UMAP is particularly good at preserving local relationships and can capture complex structures in the data.
# Combining PCA and UMAP can be beneficial because PCA can reduce noise and compress the data before applying UMAP.
# UMAP produces coordinates that can be visualized in 2D or 3D plots.

from pymongo import MongoClient
import numpy as np
import umap
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

client = MongoClient(os.environ["MONGODB_URI"])
db = client.get_database("anime")
collection = db["anime_anilist"]   # collection containing embeddings

# Fetch documents with embeddings
docs = list(collection.find({"embedding": {"$exists": True}}, {"embedding": 1, "title": 1})) # only fetch docs with embeddings
# {"embedding": {"$exists": True}} # filter to only include docs with embeddings
# {"embedding": 1, "title": 1} # projection to only include embedding and title fields

titles = [d["title"] for d in docs] # extract titles for display
embeddings = np.array([d["embedding"] for d in docs]) # convert list of lists to numpy array

print("Embedding shape:", embeddings.shape)
print("Example title:", titles[0], embeddings[0][:5])  # print first 5 dimensions of first embedding

# Step 1: Apply PCA to reduce dimensions to 50
pca = PCA(n_components=50, random_state=42) #random state 42 explained: https://stackoverflow.com/questions/49236192/what-is-the-purpose-of-random-state-in-sklearn

X_pca = pca.fit_transform(embeddings) # what this does is it fits the PCA model to the data and transforms it into the new PCA space

print("PCA reduced shape:", X_pca.shape) # should be (n_samples, 50) for 50 dimensios  
print("Original shape:", embeddings.shape) # should be (n_samples, 384) for 384 dimensions

umap_model = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, random_state=42) #random state 42 explained: https://stackoverflow.com/questions/49236192/what-is-the-purpose-of-random-state-in-sklearn
# n_neighbors: how many neighbors to consider for each point when constructing the high-dimensional graph
# min_dist: controls how tightly UMAP packs points together in the low-dimensional space
# n_components: number of dimensions for the output (2D or 3D)
# random_state: for reproducibility

X_umap = umap_model.fit_transform(X_pca) # fit UMAP model to PCA-reduced data and
print("UMAP reduced shape:", X_umap.shape) # should be (n_samples, 2) for 2 dimensions

# Plot UMAP result
plt.figure(figsize=(12, 8)) # set figure size
plt.scatter(X_umap[:, 0], X_umap[:, 1], s=5, alpha=0.7) # scatter plot of UMAP coordinates
plt.title("PCA + UMAP projection of Anime Embeddings")
plt.xlabel("UMAP Dimension 1")
plt.ylabel("UMAP Dimension 2")
plt.grid(True)
plt.show()
