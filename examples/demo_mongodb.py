# %% [markdown]
# # 🔮 cellspell — MongoDB Spell Demo
#
# Run MongoDB queries directly in Jupyter cells.
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
%%mongodb users --op insert
[
    {"name": "Alice", "age": 30, "city": "Bangkok", "role": "engineer"},
    {"name": "Bob", "age": 25, "city": "London", "role": "designer"},
    {"name": "Charlie", "age": 35, "city": "Bangkok", "role": "engineer"},
    {"name": "Diana", "age": 28, "city": "Tokyo", "role": "manager"},
    {"name": "Eve", "age": 32, "city": "London", "role": "engineer"}
]

# %% [markdown]
# ## Query Data

# %%
# Find all users (default operation is "find")
%%mongodb users
{}

# %%
# Find engineers
%%mongodb users
{"role": "engineer"}

# %%
# Find users over 30
%%mongodb users
{"age": {"$gt": 30}}

# %%
# Limit results and sort
%%mongodb users --limit 3 --sort {"age":1}
{}

# %% [markdown]
# ## Aggregation

# %%
# Count users per city
%%mongodb users --op aggregate
[
    {"$group": {"_id": "$city", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]

# %%
# Average age by role
%%mongodb users --op aggregate
[
    {"$group": {"_id": "$role", "avg_age": {"$avg": "$age"}}},
    {"$sort": {"avg_age": -1}}
]

# %% [markdown]
# ## Other Operations

# %%
# Count matching documents
%%mongodb users --op count
{"city": "Bangkok"}

# %%
# Distinct values
%%mongodb users --op distinct --field city
{}

# %% [markdown]
# ## Clean Up

# %%
%%mongodb users --op delete
{"_confirm": true}
