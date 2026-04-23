# PostgreSQL Full-Text Search

## Weighted tsvector with generated column

```sql
ALTER TABLE articles ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title,'')), 'A') ||
    setweight(to_tsvector('english', coalesce(body,'')), 'B')
  ) STORED;

CREATE INDEX ON articles USING gin (search_vector);

SELECT * FROM articles
WHERE search_vector @@ websearch_to_tsquery('english', $1)
ORDER BY ts_rank(search_vector, websearch_to_tsquery('english', $1)) DESC;
```

Weight priority: A > B > C > D. Use A for title/heading, B for body, C for metadata, D for ancillary.

## Query syntax

```sql
-- Simple search
WHERE search_vector @@ to_tsquery('english', 'postgres & replication');

-- Web-style (handles phrases, OR, negation automatically)
WHERE search_vector @@ websearch_to_tsquery('english', '"full text" search -spam');

-- Prefix matching
WHERE search_vector @@ to_tsquery('english', 'post:*');
```

## Highlighting

```sql
SELECT ts_headline('english', body,
  websearch_to_tsquery('english', $1),
  'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15'
) AS snippet
FROM articles
WHERE search_vector @@ websearch_to_tsquery('english', $1);
```

## When to use PG full-text vs external

Use PG full-text search when:
- Data is already in PostgreSQL
- Search needs are straightforward (keyword, phrase, prefix)
- Consistency matters (no sync lag between DB and search index)

Consider Elasticsearch/Typesense/Meilisearch when:
- Fuzzy matching, typo tolerance, or faceted search needed
- Search corpus exceeds ~10M documents with complex ranking
- Real-time autocomplete with sub-50ms latency required
