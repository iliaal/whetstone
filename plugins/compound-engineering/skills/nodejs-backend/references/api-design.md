# API Design Patterns

## Pagination

| Use case | Type | Why |
|----------|------|-----|
| Admin dashboards, <10K rows | Offset (`?page=2&limit=20`) | Users expect page numbers |
| Infinite scroll, feeds, large datasets | Cursor (`?cursor=abc&limit=20`) | Stable under concurrent writes |
| Search results | Offset | Users need "page 3 of 12" |

**Cursor implementation:**
```sql
SELECT * FROM items
WHERE id > :cursor_id
ORDER BY id ASC
LIMIT :limit + 1;  -- fetch N+1 to determine has_next
```

Response: `{ data, pagination: { next_cursor, has_next } }`. Encode cursor as opaque base64 to prevent client manipulation.

## Filtering

Bracket notation for comparison operators:
```
?price[gte]=10&price[lte]=100
?status[in]=active,pending
?customer.country=US          # dot notation for nested fields
```

Comma-separated for multi-value equality:
```
?category=electronics,clothing
```

## Sorting

Prefix `-` for descending, comma-separated for multi-field:
```
?sort=-created_at,name        # newest first, then alphabetical
```

## Sparse Fieldsets

```
?fields=id,name,email         # return only these fields
```

## Deprecation Protocol

1. Add `Sunset` header with retirement date: `Sunset: Sat, 01 Jan 2028 00:00:00 GMT`
2. Minimum 6-month notice before removal
3. After sunset: return `410 Gone` with migration guidance

**Breaking vs non-breaking changes:**

| Non-breaking (no new version) | Breaking (requires new version) |
|-------------------------------|--------------------------------|
| Adding optional fields/params | Removing or renaming fields |
| Adding new endpoints | Changing field types |
| Adding new enum values | Removing endpoints |
| Relaxing validation | Tightening validation |
| Extending response with new keys | Changing response structure |
