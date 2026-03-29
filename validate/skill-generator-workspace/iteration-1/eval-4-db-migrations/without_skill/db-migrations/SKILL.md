---
name: db-migrations
description: >
  PostgreSQL database migration management with Knex.js. Create, modify, and rollback
  schema migrations including tables, columns, indexes, constraints, enums, and data
  transforms. Use when user asks to "create a migration", "add a column", "change schema",
  "alter table", "rollback migration", "create table", "add index", "rename column",
  "database migration", "knex migrate", or needs help with any PostgreSQL schema change
  in a Node.js/Knex project.
---

# Database Migrations with Knex.js + PostgreSQL

You help users create, manage, and troubleshoot database migrations using **Knex.js** against **PostgreSQL**. Every migration must be safe, reversible, and production-ready.

## Quick Start

When the user asks for a migration, follow this workflow:

1. **Discover** the project's migration setup
2. **Generate** the migration file
3. **Verify** it compiles and the rollback is complete
4. Optionally **run** the migration if the user asks

---

## Step 1 — Discover the Project

Before writing any migration, gather context:

```bash
# Find the knexfile
find . -maxdepth 3 -name "knexfile.*" -o -name "knex.config.*" 2>/dev/null

# Find existing migrations directory
find . -type d -name "migrations" 2>/dev/null

# Look at the most recent migration for naming/style conventions
ls -t $(find . -type d -name "migrations" | head -1) 2>/dev/null | head -5
```

Read the `knexfile.js` (or `.ts`) to determine:
- Which `migrations.directory` is configured
- The `migrations.stub` if a custom stub exists
- Whether the project uses JavaScript or TypeScript

Read the 1-2 most recent migration files to match the project's existing style (arrow functions vs named functions, `async/await` vs `.then()`, etc.).

---

## Step 2 — Generate the Migration

### Create the file

Use the Knex CLI to create a properly timestamped migration:

```bash
npx knex migrate:make <descriptive_name>
```

If the CLI is unavailable, create the file manually with the timestamp format `YYYYMMDDHHMMSS_<name>.js` (or `.ts`).

### Naming conventions

Use snake_case, verb-first names that describe the change:

| Change | Name |
|---|---|
| New table | `create_users` |
| Add column(s) | `add_email_to_users` |
| Remove column | `remove_legacy_flag_from_orders` |
| Add index | `add_index_on_users_email` |
| Rename column | `rename_username_to_handle_in_users` |
| Alter column type | `change_price_to_decimal_in_products` |
| Add foreign key | `add_fk_orders_user_id` |
| Create enum | `create_status_enum` |
| Data backfill | `backfill_users_display_name` |

### Migration template (JavaScript)

```js
/**
 * @param {import('knex').Knex} knex
 */
exports.up = async function (knex) {
  // forward migration
};

/**
 * @param {import('knex').Knex} knex
 */
exports.down = async function (knex) {
  // MUST fully reverse exports.up
};
```

### Migration template (TypeScript)

```ts
import { Knex } from 'knex';

export async function up(knex: Knex): Promise<void> {
  // forward migration
}

export async function down(knex: Knex): Promise<void> {
  // MUST fully reverse exports.up
}
```

---

## Schema Operations Reference

### Create a table

```js
exports.up = async function (knex) {
  await knex.schema.createTable('users', (table) => {
    table.increments('id').primary();
    table.string('email', 255).notNullable().unique();
    table.string('name', 255).notNullable();
    table.text('bio');
    table.boolean('is_active').notNullable().defaultTo(true);
    table.timestamps(true, true); // created_at, updated_at with defaults
  });
};

exports.down = async function (knex) {
  await knex.schema.dropTableIfExists('users');
};
```

### Add column(s)

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.string('phone', 20);
    table.integer('age');
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropColumn('phone');
    table.dropColumn('age');
  });
};
```

### Drop column(s)

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropColumn('legacy_field');
  });
};

exports.down = async function (knex) {
  // Restore the column with its original type and constraints
  await knex.schema.alterTable('users', (table) => {
    table.string('legacy_field', 255).defaultTo('');
  });
};
```

### Rename a column

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.renameColumn('username', 'handle');
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.renameColumn('handle', 'username');
  });
};
```

### Change column type / constraints

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('products', (table) => {
    table.decimal('price', 10, 2).notNullable().defaultTo(0).alter();
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('products', (table) => {
    table.integer('price').alter();
  });
};
```

> **Note:** `.alter()` requires the `knex` peer dependency on the npm package `pg`. It uses `ALTER COLUMN ... TYPE ... USING` under the hood.

### Add an index

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('orders', (table) => {
    table.index(['user_id', 'created_at'], 'idx_orders_user_created');
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('orders', (table) => {
    table.dropIndex(['user_id', 'created_at'], 'idx_orders_user_created');
  });
};
```

### Add a unique constraint

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.unique(['org_id', 'email'], { indexName: 'uq_users_org_email' });
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropUnique(['org_id', 'email'], 'uq_users_org_email');
  });
};
```

### Foreign keys

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('orders', (table) => {
    table
      .integer('user_id')
      .unsigned()
      .notNullable()
      .references('id')
      .inTable('users')
      .onDelete('CASCADE')
      .onUpdate('CASCADE');
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('orders', (table) => {
    table.dropForeign('user_id');
    table.dropColumn('user_id');
  });
};
```

### PostgreSQL enums

```js
exports.up = async function (knex) {
  // Create enum type first, then use it
  await knex.raw(`CREATE TYPE order_status AS ENUM ('pending', 'shipped', 'delivered', 'cancelled')`);
  await knex.schema.alterTable('orders', (table) => {
    table.specificType('status', 'order_status').notNullable().defaultTo('pending');
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('orders', (table) => {
    table.dropColumn('status');
  });
  await knex.raw('DROP TYPE IF EXISTS order_status');
};
```

### Add a value to an existing enum

```js
exports.up = async function (knex) {
  // ALTER TYPE ... ADD VALUE cannot run inside a transaction in PostgreSQL
  await knex.raw(`ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'refunded'`);
};

exports.down = async function (knex) {
  // PostgreSQL does NOT support removing a single enum value.
  // Removing requires recreating the type. Only do this if truly needed:
  //
  // 1. Rename old type
  // 2. Create new type without the value
  // 3. Alter columns to use new type
  // 4. Drop old type
  //
  // If the value was never used in data, this is safe. If it was, the down
  // migration must also UPDATE rows first. Log a warning instead if rollback
  // is impractical.
  console.warn('Down migration for enum value removal is a no-op. Manual intervention required to remove enum value.');
};
```

### Data backfill migration

```js
exports.up = async function (knex) {
  // Add column
  await knex.schema.alterTable('users', (table) => {
    table.string('display_name', 255);
  });

  // Backfill in batches to avoid locking the table
  const BATCH_SIZE = 1000;
  let offset = 0;
  let updated;

  do {
    updated = await knex.raw(`
      UPDATE users
      SET display_name = name
      WHERE id IN (
        SELECT id FROM users
        WHERE display_name IS NULL
        ORDER BY id
        LIMIT ?
      )
    `, [BATCH_SIZE]);

    offset += BATCH_SIZE;
  } while (updated.rowCount > 0);

  // Now make it NOT NULL
  await knex.schema.alterTable('users', (table) => {
    table.string('display_name', 255).notNullable().alter();
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropColumn('display_name');
  });
};
```

### Raw SQL (when Knex schema builder is insufficient)

```js
exports.up = async function (knex) {
  await knex.raw(`
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower
    ON users (LOWER(email))
  `);
};

exports.down = async function (knex) {
  await knex.raw('DROP INDEX IF EXISTS idx_users_email_lower');
};
```

> **Important:** `CREATE INDEX CONCURRENTLY` cannot run inside a transaction. You must disable the Knex migration transaction for this migration. See the "Disabling transactions" section.

### Disabling the migration transaction

Some PostgreSQL operations (`CREATE INDEX CONCURRENTLY`, `ALTER TYPE ... ADD VALUE`) cannot run inside a transaction. Export a config object:

```js
// For JS migrations
exports.config = { transaction: false };
```

```ts
// For TS migrations
export const config = { transaction: false };
```

---

## Running Migrations

```bash
# Run all pending migrations
npx knex migrate:latest

# Rollback the last batch
npx knex migrate:rollback

# Rollback ALL migrations (dangerous in production)
npx knex migrate:rollback --all

# Check current migration status
npx knex migrate:status

# Run against a specific environment
npx knex migrate:latest --env production
```

---

## Critical Rules

These rules are NON-NEGOTIABLE. Every migration you generate must follow them.

### 1. Every `up` must have a complete `down`

The `down` function must **fully reverse** what `up` did. If `up` creates a table, `down` drops it. If `up` adds three columns, `down` drops all three. A missing or incomplete `down` is a bug.

**Exception:** Adding a value to a PostgreSQL enum cannot be cleanly reversed. Document this clearly with a comment in the `down` function.

### 2. Migrations must be idempotent-safe

Use guards where possible:
- `createTableIfNotExists` / `dropTableIfExists`
- `IF NOT EXISTS` / `IF EXISTS` in raw SQL
- Check column existence before adding with `hasColumn()`

### 3. Never modify a migration that has been run

If a migration has already been applied (to any environment), **never edit it**. Create a new migration to fix or change the schema. Editing applied migrations causes drift between the migration history and the actual schema.

### 4. One logical change per migration

Each migration file should make one cohesive change. Don't combine unrelated schema changes.

### 5. Production safety

- **Never** drop a column that is still read by application code. Deploy the code change first, then migrate.
- **Add columns as nullable** (or with a default) to avoid full table rewrites/locks on large tables.
- Use `CREATE INDEX CONCURRENTLY` for indexes on large tables (requires `config.transaction = false`).
- Batch data updates to avoid long-running locks.
- **Always test rollback** locally before deploying.

### 6. Use explicit index/constraint names

Always provide explicit names for indexes, unique constraints, and foreign keys. Auto-generated names vary across environments and make rollbacks fragile.

### 7. Handle the `timestamps()` helper carefully

`table.timestamps(true, true)` creates `created_at` and `updated_at` with `defaultTo(knex.fn.now())`. The second argument makes both columns `NOT NULL`. Be explicit about this in the `down` migration.

---

## Troubleshooting

### "migration is already locked"

```bash
# Check and manually unlock (only if no migration is actually running)
npx knex migrate:unlock
```

Or directly in PostgreSQL:

```sql
SELECT * FROM knex_migrations_lock;
UPDATE knex_migrations_lock SET is_locked = 0;
```

### Migration failed mid-way

If a migration fails partway through and the transaction was enabled (default), the entire migration is rolled back automatically. If the transaction was disabled (`config.transaction = false`), you may have a partial migration. Inspect the schema and either:
1. Fix the issue and re-run
2. Manually complete or revert the partial changes, then re-run

### Column type mismatch on `.alter()`

The `.alter()` method generates `ALTER COLUMN ... TYPE ... USING column::new_type`. If the cast is not implicit (e.g., `text` to `integer`), provide a raw `USING` clause:

```js
await knex.raw(`
  ALTER TABLE products
  ALTER COLUMN price TYPE integer USING price::integer
`);
```

### Enum type already exists

```js
// Safe creation
await knex.raw(`
  DO $$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'my_enum') THEN
      CREATE TYPE my_enum AS ENUM ('a', 'b', 'c');
    END IF;
  END
  $$;
`);
```

---

## Workflow Checklist

When generating a migration, mentally verify:

- [ ] File is named with verb-first snake_case describing the change
- [ ] `up` implements the full forward change
- [ ] `down` fully reverses `up` (or documents why it cannot)
- [ ] Explicit names on all indexes, constraints, and foreign keys
- [ ] New columns are nullable or have defaults (production safety)
- [ ] Large table operations use `CONCURRENTLY` / batching where appropriate
- [ ] Transaction is disabled if using `CONCURRENTLY` or `ALTER TYPE ... ADD VALUE`
- [ ] Matches the project's existing code style (JS vs TS, async vs callbacks)
