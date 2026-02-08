"""cellspell.spells.mongodb — MongoDB cell magic (planned).

Will support:
    %mongo_connect mongodb://localhost:27017/mydb
    %%mongodb
    db.users.find({ "age": { "$gt": 25 } })

Backend:
    - PyMongo
"""

# TODO: Implement MongoDB spell


def load_ipython_extension(ipython):
    raise NotImplementedError(
        "MongoDB spell is not yet implemented. Coming soon!\n"
        "Track progress at: https://github.com/yourusername/cellspell"
    )


def unload_ipython_extension(ipython):
    pass
