# **Module 1: The Evolution of the Database**

**Context:** Understanding how we moved from "Classic SQL" to "AI-Native Postgres."

## **1.1 The "Classic" Relational Model (What you learned)**

In your undergrad class, you likely learned that a database is a collection of rigid tables.

* **The Analogy:** An Excel Workbook where every sheet is locked. You cannot type a "Date" into a "Number" column.  
* **The Schema:** You must define everything upfront.  
  CREATE TABLE books (  
      id INTEGER PRIMARY KEY,  
      title VARCHAR(255),  
      author VARCHAR(255)  
  );

* **The Strength:** **Data Integrity.** You can never have a book without a title. The database prevents mistakes.  
* **The Weakness:** **Rigidity.** If one book has a "translator" and another doesn't, you have to add a translator column to the *entire* table and fill it with NULLs for everyone else.

## **1.2 The "NoSQL" Revolution (The Document Model)**

Developers got tired of rigid schemas. They wanted to just "save the object."

* **The Analogy:** A box of file folders. You can throw a receipt, a photo, and a letter into the same folder.  
* **The Schema:** There is none.  
  { "title": "Green Line", "unit": 1, "vocabulary": \["apple", "dog"\] }

* **The Strength:** **Flexibility.** Perfect for "messy" data like textbooks where every page is different.  
* **The Weakness:** **Chaos.** If you misspell "title" as "titel", the database won't stop you. Queries become hard ("Find all books" might miss the misspelled ones).

## **1.3 The Modern Hybrid: PostgreSQL (Our Project)**

PostgreSQL is unique because it is a **Relational Engine** that learned how to be **NoSQL**.

* **The Feature:** JSONB. It allows a column to behave like a NoSQL document store.  
* **Why we use it:** We keep the "Spine" relational (IDs, Foreign Keys) but make the "Flesh" flexible (Content, Metadata).

# **Module 2: Understanding Vector Databases**

**Context:** How machines "read" meaning.

## **2.1 What is a Vector?**

To a computer, the word "Apple" is just 5 bytes: 0x41 0x70 0x70 0x6C 0x65. It has no meaning. It's just a label.  
To an AI model (like OpenAI or Gemini), "Apple" is a point in a multi-dimensional concept space.

* **The Representation:** \[0.9, 0.1, \-0.5, ...\] (A list of 1,536 numbers).  
* **The Meaning:** These numbers represent coordinates.  
  * Dimension 1 might be "Edible vs. Inedible".  
  * Dimension 2 might be "Technology vs. Nature".  
  * "Apple" (Fruit) is close to "Pear."  
  * "Apple" (iPhone) is close to "Microsoft."

## **2.2 Vector Search vs. Keyword Search**

* **Keyword Search (SQL LIKE):**  
  * Query: "Mobile Phone"  
  * Database: Looks for the exact string "Mobile Phone".  
  * Result: Misses "iPhone", "Android", "Cellular Device."  
* **Vector Search (Semantic):**  
  * Query: "Mobile Phone" \-\> Converted to Vector \[0.1, 0.8...\].  
  * Database: Calculates the **Cosine Distance** (angle) between this vector and all stored vectors.  
  * Result: "iPhone" has a very small distance (angle) from "Mobile Phone." It is a match.

## **2.3 The HNSW Index (The Magic Graph)**

Searching 1 million vectors by calculating the distance to *each one* is too slow. We need an index.

* **B-Tree (Classic SQL):** Works for sorting (A-Z, 1-10). Vectors cannot be sorted.  
* **HNSW (Hierarchical Navigable Small World):** A graph structure.  
  * Imagine a "Friend Network."  
  * You ask "Alice" (Entry Node): "Do you know 'Nuclear Physics'?"  
  * Alice says: "No, but my friend 'Bob' is a scientist. Go ask him."  
  * You jump to Bob. Bob is closer. He guides you to the "Physics" neighborhood.  
  * **Result:** You find the answer in 5 hops instead of checking 1 million rows.

# **Module 3: Scaling Strategies (Sharding vs. Partitioning)**

**Context:** What happens when we have 10,000 textbooks?

## **3.1 The Problem: The "Fat Table"**

If you put all data into one table (content\_atoms), it grows to 100 million rows.

* **Index Bloat:** The index becomes larger than the server's RAM.  
* **Slowdown:** Searching "Green Line 1" requires scanning through index entries for "Green Line 2", "Physics 101", etc.

## **3.2 Solution A: Sharding (The "Hard" Way)**

You buy 10 database servers.

* Server 1 holds Books 1-1000.  
* Server 2 holds Books 1001-2000.  
* **Pros:** Infinite scale.  
* **Cons:** Your application code needs to know which server to talk to. Complex to manage.

## **3.3 Solution B: Partitioning (The "Smart" Way)**

You use one server, but tell Postgres to split the table into 10,000 small files.

* **The Illusion:** The application sees one table: content\_atoms.  
* **The Reality:** On the hard drive, there are 10,000 separate files (content\_book\_1, content\_book\_2).  
* **The Performance:** When you query WHERE book\_id \= '1', Postgres **only opens File \#1**. It ignores the other 9,999. It is essentially instant.

# **Module 4: The Textbook RAG Architecture**

**Context:** Putting it all together for your project.

## **4.1 The "Hybrid" Query**

We rarely use *just* Vectors or *just* SQL. We use **Hybrid Search**.

* **Teacher Query:** "Find me a quiz on **football** for **Unit 1**."  
* **Step 1 (SQL/Metadata):** "Filter unit\_number \= 1."  
  * This discards 90% of the data (Units 2-10). We are left with a small "Subspace."  
* **Step 2 (Vector):** "Search for 'football' in the remaining data."  
  * We run HNSW search only on that small subspace.  
* **Result:** Extremely fast and accurate.

## **4.2 Why LlamaIndex?**

LlamaIndex is a framework that automates the "Hybrid" dance.

1. It creates the text and embedding columns.  
2. It creates the metadata JSON column.  
3. When you pass a filter MetadataFilter(unit=1), it automatically writes the SQL WHERE metadata\_-\>\>'unit' \= '1'.  
4. It automatically combines this with the Vector search.

## **4.3 Why Gemini Vision for Ingestion?**

Textbooks are visual.

* **Old Way (OCR):** Extracts text line-by-line. Loses the fact that the word "Apple" was next to a picture of an Apple.  
* **New Way (Multimodal):** Gemini "looks" at the page. It sees the visual relationship. It generates a description: *"An exercise box containing the word 'Apple' with an illustration."* This description is what we embed.

# **Final Review Questions**

1. **Why do we use metadata\_ JSONB instead of columns like unit\_number?**  
   * *Answer:* Flexibility. Different textbooks have different structures (Units vs. Chapters). JSONB lets us adapt without changing the database schema.  
2. **Why is Vector Search "Approximate"?**  
   * *Answer:* Because it uses a Graph (HNSW) to "hop" towards the answer rather than checking every single row (which would be too slow).  
3. **What is the benefit of Partitioning for this project?**  
   * *Answer:* It keeps search fast even if we host 10,000 books, because a query for one book never has to look at the data for the other 9,999.