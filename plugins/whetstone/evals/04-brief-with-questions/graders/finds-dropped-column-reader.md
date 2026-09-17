---
type: llm
focus: last_message
---
The diff drops `products.legacy_code` but `Product::getDisplaySkuAttribute()` (an unchanged context line in the diff) still reads `$this->legacy_code`. After the migration this accessor silently returns the bare sku (the missing attribute is null on Eloquent models), so the display sku changes for every product that had a legacy code. Pass only if:
1. The review identifies that `getDisplaySkuAttribute` still references the dropped column.
2. It ranks this Critical or Important (or an equivalent top-two label).
