---
max_turns: 20
timeout_seconds: 420
allowed_tools: [Skill, Read, Glob, Grep]
runs: 3
---
Use the ia-code-review skill for this. Audit this file for code quality. There is no repo and no diff; this is the whole file.

```ts
// src/repo/order-repo.ts
import { Pool } from "pg";
import { Order } from "../types";

export class OrderRepo {
  constructor(private pool: Pool) {}

  async createOrder(order: Order): Promise<number> {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const res: any = await client.query(
        "INSERT INTO orders (customer_id, total) VALUES ($1, $2) RETURNING id",
        [order.customerId, order.total],
      );
      const orderId = res.rows[0].id;
      for (const line of order.lines) {
        await client.query(
          "INSERT INTO order_lines (order_id, sku, qty) VALUES ($1, $2, $3)",
          [orderId, line.sku, line.qty],
        );
      }
      client.query("COMMIT");
      console.log("order created", orderId);
      return orderId;
    } catch (err: any) {
      await client.query("ROLLBACK");
      throw err;
    } finally {
      client.release();
    }
  }
}
```
