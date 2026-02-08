# %% [markdown]
# # 🔮 cellspell — MongoDB Spell Demo
#
# Run MongoDB queries directly in Jupyter cells using mongosh syntax.
#
# ## Prerequisites
#
# - A running MongoDB instance
# - `pip install cellspell[mongodb]`

# %%
# !pip install cellspell[mongodb] -q  # Uncomment to install

# %%
%load_ext cellspell.mongodb

# %% [markdown]
# ## Connect to MongoDB

# %%
%mongo_connect mongodb://localhost:27017/demo

# %%
%mongo_info

# %% [markdown]
# ## Insert Sample Data

# %%
%%mongodb
db.users.insertMany([
    {"name": "Alice", "age": 30, "city": "Bangkok", "role": "engineer"},
    {"name": "Bob", "age": 25, "city": "London", "role": "designer"},
    {"name": "Charlie", "age": 35, "city": "Bangkok", "role": "engineer"},
    {"name": "Diana", "age": 28, "city": "Tokyo", "role": "manager"},
    {"name": "Eve", "age": 32, "city": "London", "role": "engineer"}
])

# %% [markdown]
# ## Query Data

# %%
# Find all users
%%mongodb
db.users.find()

# %%
# Find engineers
%%mongodb
db.users.find({"role": "engineer"})

# %%
# Find users over 30, sort by age
%%mongodb
db.users.find({"age": {"$gt": 30}}).sort({"age": -1})

# %%
# Find with projection — only name and city
%%mongodb
db.users.find({}, {"name": 1, "city": 1, "_id": 0})

# %%
# Find first 3 users sorted by age
%%mongodb
db.users.find().sort({"age": 1}).limit(3)

# %%
# Find one user
%%mongodb
db.users.findOne({"name": "Alice"})

# %% [markdown]
# ## Aggregation

# %%
# Count users per city
%%mongodb
db.users.aggregate([
    {"$group": {"_id": "$city", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])

# %%
# Average age by role
%%mongodb
db.users.aggregate([
    {"$group": {"_id": "$role", "avg_age": {"$avg": "$age"}}},
    {"$sort": {"avg_age": -1}}
])

# %% [markdown]
# ## Other Operations

# %%
# Count matching documents
%%mongodb
db.users.countDocuments({"city": "Bangkok"})

# %%
# Distinct cities
%%mongodb
db.users.distinct("city")

# %%
# Update a document
%%mongodb
db.users.updateOne({"name": "Alice"}, {"$set": {"age": 31}})

# %%
# Verify the update
%%mongodb
db.users.findOne({"name": "Alice"})

# %% [markdown]
# ## Inline Connection
#
# You can also connect and query in a single cell:

# %%
%%mongodb mongodb://localhost:27017/demo
db.users.find({"role": "engineer"}).sort({"name": 1})

# %% [markdown]
# ## Clean Up

# %%
%%mongodb
db.users.drop()
