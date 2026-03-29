---
name: db-migrations
description: >
  Create, manage, and troubleshoot Knex.js database migrations for PostgreSQL.
  Use this skill when the user wants to create a migration, alter a table, add or drop columns,
  create indexes, rename fields, change column types, write rollback logic, or manage migration history.
  Also use when the user says "knex migrate", "schema change", "add column", "create table",
  "database migration", "rollback migration", "migration file", "alter table", "drop column",
  "knex seed", or asks how to safely change their PostgreSQL schema in a Node.js project.
  Also triggers when the user has a failing migration, wants to squash migrations,
  or needs to handle data migrations alongside schema changes.
  Do NOT use for ORM query building, Prisma/TypeORM/Sequelize migrations (those use different
  CLIs and file formats), or general SQL query writing unrelated to schema changes.
---

# Database Migrations with Knex.js + PostgreSQL

Write safe, reversible Knex migrations that modify PostgreSQL schemas without data loss.

## Why this matters

A bad migration can drop production data or lock tables for minutes. Every migration must:
- Be **reversible** -- the `down` function must undo exactly what `up` did
- Be **idempotent-safe** -- avoid assumptions about current schema state
- Handle **data preservation** -- when altering columns, migrate data before dropping
- Use **transactions** -- wrap multi-step changes so they succeed or fail atomically

## Workflow

### 1. Create the migration file

Run the Knex CLI to scaffold a timestamped migration:

```bash
npx knex migrate:make <descriptive_name>
```

**Naming conventions** -- use snake_case verbs that describe the change:

| Change | Name example |
|--------|-------------|
| New table | `create_users_table` |
| Add column(s) | `add_email_to_users` |
| Remove column | `drop_legacy_status_from_orders` |
| Add index | `add_index_on_users_email` |
| Rename column | `rename_name_to_full_name_in_users` |
| Change column type | `change_price_to_decimal_in_products` |
| Data migration | `backfill_users_display_name` |
| Multiple tables | `create_posts_and_comments_tables` |

### 2. Write the `up` and `down` functions

Every migration exports two functions. Follow these rules:

**Always write `down` as the exact inverse of `up`.**
If `up` creates a table, `down` drops it. If `up` adds a column, `down` drops that column.
If `up` changes a column type, `down` reverts to the original type.

**Use `alterTable` for column changes, `createTable` for new tables.**

**Use transactions for multi-step migrations:**

```js
exports.up = async function(knex) {
  await knex.transaction(async (trx) => {
    await trx.schema.createTable('posts', (table) => {
      table.increments('id').primary();
      table.integer('user_id').unsigned().notNullable()
        .references('id').inTable('users').onDelete('CASCADE');
      table.string('title', 255).notNullable();
      table.text('body');
      table.timestamps(true, true);
    });

    await trx.schema.alterTable('users', (table) => {
      table.integer('post_count').defaultTo(0);
    });
  });
};

exports.down = async function(knex) {
  await knex.transaction(async (trx) => {
    await trx.schema.alterTable('users', (table) => {
      table.dropColumn('post_count');
    });
    await trx.schema.dropTableIfExists('posts');
  });
};
```

**For TypeScript projects:**

```ts
import { Knex } from 'knex';

export async function up(knex: Knex): Promise<void> {
  await knex.schema.createTable('posts', (table) => {
    table.increments('id').primary();
    table.string('title', 255).notNullable();
    table.timestamps(true, true);
  });
}

export async function down(knex: Knex): Promise<void> {
  await knex.schema.dropTableIfExists('posts');
}
```

### 3. Handle common schema changes

#### Add a column

```js
exports.up = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.string('phone', 20).nullable();
  });
};

exports.down = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropColumn('phone');
  });
};
```

#### Add a NOT NULL column to a table with existing data

Cannot add NOT NULL without a default or backfill. Use a three-step approach:

```js
exports.up = async function(knex) {
  await knex.transaction(async (trx) => {
    // 1. Add as nullable
    await trx.schema.alterTable('users', (table) => {
      table.string('display_name', 100).nullable();
    });

    // 2. Backfill existing rows
    await trx.raw(`UPDATE users SET display_name = first_name || ' ' || last_name`);

    // 3. Set NOT NULL constraint
    await trx.raw(`ALTER TABLE users ALTER COLUMN display_name SET NOT NULL`);
  });
};

exports.down = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropColumn('display_name');
  });
};
```

#### Rename a column

```js
exports.up = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.renameColumn('name', 'full_name');
  });
};

exports.down = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.renameColumn('full_name', 'name');
  });
};
```

#### Change a column type

```js
exports.up = async function(knex) {
  await knex.schema.alterTable('products', (table) => {
    table.decimal('price', 10, 2).alter();
  });
};

exports.down = async function(knex) {
  await knex.schema.alterTable('products', (table) => {
    table.integer('price').alter();
  });
};
```

> Note: `alter()` requires the `knex` version 0.20+ and may need raw SQL for some
> PostgreSQL-specific type changes.

#### Add an index

```js
exports.up = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.index('email', 'idx_users_email');
  });
};

exports.down = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropIndex('email', 'idx_users_email');
  });
};
```

#### Add a unique constraint

```js
exports.up = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.unique('email');
  });
};

exports.down = async function(knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropUnique('email');
  });
};
```

#### Create an enum column (PostgreSQL native enum)

```js
exports.up = async function(knex) {
  await knex.raw(`CREATE TYPE order_status AS ENUM ('pending', 'shipped', 'delivered', 'cancelled')`);
  await knex.schema.alterTable('orders', (table) => {
    table.specificType('status', 'order_status').defaultTo('pending');
  });
};

exports.down = async function(knex) {
  await knex.schema.alterTable('orders', (table) => {
    table.dropColumn('status');
  });
  await knex.raw(`DROP TYPE order_status`);
};
```

### 4. Run and manage migrations

| Task | Command |
|------|---------|
| Run pending migrations | `npx knex migrate:latest` |
| Rollback last batch | `npx knex migrate:rollback` |
| Rollback all | `npx knex migrate:rollback --all` |
| Run one migration forward | `npx knex migrate:up` |
| Undo one migration | `npx knex migrate:down` |
| Check migration status | `npx knex migrate:status` |
| List completed migrations | `npx knex migrate:list` |
| Run in specific environment | `npx knex migrate:latest --env production` |

### 5. Handle rollback safety

Before running any destructive migration in production:

1. **Take a database backup** -- `pg_dump dbname > backup_before_migration.sql`
2. **Test on a staging copy first** -- never run untested migrations in production
3. **Verify the `down` function works** -- run `migrate:latest` then `migrate:rollback`
4. **Check for table locks** -- adding indexes on large tables can lock them; use `CREATE INDEX CONCURRENTLY` via raw SQL instead

#### Concurrent index creation (avoids table lock)

```js
exports.up = async function(knex) {
  // Cannot run inside a transaction -- CONCURRENTLY prevents that
  await knex.raw(`CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders (user_id)`);
};

exports.down = async function(knex) {
  await knex.raw(`DROP INDEX IF EXISTS idx_orders_user_id`);
};
```

> Disable the automatic Knex transaction wrapper for this migration by setting
> `exports.config = { transaction: false };` at the bottom of the file.

### 6. Knexfile configuration

Ensure `knexfile.js` (or `knexfile.ts`) is configured properly:

```js
module.exports = {
  development: {
    client: 'pg',
    connection: {
      host: '127.0.0.1',
      port: 5432,
      user: 'devuser',
      password: 'devpass',
      database: 'myapp_dev',
    },
    migrations: {
      directory: './migrations',
      tableName: 'knex_migrations',
    },
    seeds: {
      directory: './seeds',
    },
  },
  production: {
    client: 'pg',
    connection: process.env.DATABASE_URL,
    migrations: {
      directory: './migrations',
      tableName: 'knex_migrations',
    },
    pool: { min: 2, max: 10 },
  },
};
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "migration table is already locked" | Previous migration crashed | `DELETE FROM knex_migrations_lock WHERE is_locked = 1;` |
| "column already exists" | Migration ran partially | Check schema, manually fix, or reset lock and re-run |
| "relation does not exist" | Table not created yet / wrong order | Check timestamps on migration filenames -- earlier timestamp runs first |
| `alter()` fails | Knex version too old or unsupported PG type change | Use `knex.raw('ALTER TABLE ...')` instead |
| Rollback drops data | `down` dropped a column with data | Add a data backup step before dropping, or accept data loss in dev |
| Timeout on large table | ALTER TABLE locks large table | Use batched updates and concurrent indexes |

## Decision guide: Knex schema builder vs raw SQL

| Situation | Use |
|-----------|-----|
| Standard create/alter/drop | Knex schema builder |
| PostgreSQL-specific features (enums, partitions, extensions) | `knex.raw()` |
| Concurrent index creation | `knex.raw()` with `exports.config = { transaction: false }` |
| Complex data backfills with joins | `knex.raw()` or knex query builder |
| Anything the schema builder doesn't support | `knex.raw()` |

## Reference

For a quick reference of common PostgreSQL column types and their Knex equivalents,
see `references/pg-column-types.md`.
