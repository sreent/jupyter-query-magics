# %% [markdown]
# # 🔮 cellspell Demo
#
# Demonstrating the XPath spell.
#
# ## Setup

# %%
# !apt-get install -y libxml2-utils -qq  # Uncomment for Colab
# !pip install cellspell -q              # Uncomment for Colab

# %%
%load_ext cellspell

# %% [markdown]
# ## Create Sample XML Files

# %%
%%writefile books.xml
<?xml version="1.0"?>
<bookstore>
    <book category="fiction">
        <title lang="en">The Great Gatsby</title>
        <author>F. Scott Fitzgerald</author>
        <year>1925</year>
        <price>10.99</price>
    </book>
    <book category="tech">
        <title lang="en">Python Cookbook</title>
        <author>David Beazley</author>
        <year>2013</year>
        <price>39.99</price>
    </book>
    <book category="tech">
        <title lang="th">Database Systems</title>
        <author>Ramez Elmasri</author>
        <year>2015</year>
        <price>45.00</price>
    </book>
    <book category="fiction">
        <title lang="en">1984</title>
        <author>George Orwell</author>
        <year>1949</year>
        <price>8.99</price>
    </book>
</bookstore>

# %% [markdown]
# ## Load and Validate

# %%
%xpath_load books.xml

# %%
%xpath_validate books.xml

# %%
%xpath_info

# %% [markdown]
# ## Basic Queries

# %%
# Get all book titles
%%xpath
//book/title/text()

# %%
# Get tech book titles
%%xpath
//book[@category='tech']/title/text()

# %%
# Books over $30
%%xpath
//book[price > 30]/title/text()

# %%
# Count books
%%xpath
count(//book)

# %%
# Get all authors (sorted is XPath 1.0 — no sort, just retrieval)
%%xpath
//book/author/text()

# %%
# Get titles in Thai language
%%xpath
//book/title[@lang='th']/text()

# %% [markdown]
# ## Formatted XML Output

# %%
%%xpath --format
//book[@category='tech']

# %%
%%xpath --format
//book[year < 1950]

# %% [markdown]
# ## HTML Parsing

# %%
%%writefile page.html
<html>
<body>
    <nav>
        <a href="/home">Home</a>
        <a href="/about">About</a>
    </nav>
    <div class="content">
        <h1>Welcome</h1>
        <ul>
            <li class="item">Item 1</li>
            <li class="item">Item 2</li>
            <li class="item">Item 3</li>
        </ul>
        <a href="https://example.com">External Link</a>
    </div>
</body>
</html>

# %%
%%xpath --html page.html
//div[@class='content']//li/text()

# %%
%%xpath --html page.html
//a/@href

# %% [markdown]
# ## Query a Different File Inline

# %%
%%writefile employees.xml
<?xml version="1.0"?>
<company>
    <department name="Engineering">
        <employee id="1">
            <name>Alice</name>
            <role>Senior Engineer</role>
            <salary>120000</salary>
        </employee>
        <employee id="2">
            <name>Bob</name>
            <role>DevOps</role>
            <salary>110000</salary>
        </employee>
    </department>
    <department name="Marketing">
        <employee id="3">
            <name>Charlie</name>
            <role>Content Lead</role>
            <salary>95000</salary>
        </employee>
    </department>
</company>

# %%
%%xpath employees.xml
//department[@name='Engineering']/employee/name/text()

# %%
%%xpath --format employees.xml
//employee[salary > 100000]

# %%
%%xpath employees.xml
count(//employee)
