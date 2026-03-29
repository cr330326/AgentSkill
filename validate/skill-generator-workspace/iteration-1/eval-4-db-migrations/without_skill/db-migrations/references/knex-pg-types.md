# Knex.js ↔ PostgreSQL Type Mapping Reference

## Column Types

| Knex Method | PostgreSQL Type | Notes |
|---|---|---|
| `table.increments('id')` | `serial PRIMARY KEY` | Auto-incrementing integer |
| `table.bigIncrements('id')` | `bigserial PRIMARY KEY` | Auto-incrementing bigint |
| `table.uuid('id')` | `uuid` | Pair with `.defaultTo(knex.fn.uuid())` (Knex 2.5+) or `knex.raw('gen_random_uuid()')` |
| `table.string('col')` | `varchar(255)` | Default length 255 |
| `table.string('col', 100)` | `varchar(100)` | Explicit length |
| `table.text('col')` | `text` | Unlimited length |
| `table.integer('col')` | `integer` | 4-byte signed |
| `table.bigInteger('col')` | `bigint` | 8-byte signed |
| `table.float('col')` | `real` | 4-byte float |
| `table.double('col')` | `double precision` | 8-byte float |
| `table.decimal('col', 10, 2)` | `numeric(10,2)` | Exact decimal |
| `table.boolean('col')` | `boolean` | |
| `table.date('col')` | `date` | |
| `table.datetime('col')` | `timestamptz` | With timezone (Knex default for PG) |
| `table.timestamp('col')` | `timestamptz` | Same as datetime |
| `table.time('col')` | `time` | |
| `table.binary('col')` | `bytea` | |
| `table.json('col')` | `json` | Stored as text, validated on insert |
| `table.jsonb('col')` | `jsonb` | Binary, indexable, queryable |
| `table.enum('col', [...])` | Creates a CHECK constraint | Use `specificType` for PG native enums |
| `table.specificType('col', 'type')` | Any PG type | For arrays, enums, custom types |

## Common PostgreSQL-Specific Types via `specificType`

```js
table.specificType('tags', 'text[]');              // text array
table.specificType('scores', 'integer[]');          // integer array
table.specificType('location', 'point');             // geometric point
table.specificType('ip', 'inet');                    // IP address
table.specificType('mac', 'macaddr');                // MAC address
table.specificType('search', 'tsvector');            // full-text search
table.specificType('range', 'int4range');             // integer range
table.specificType('money', 'money');                // monetary
```

## Column Modifiers

| Modifier | Effect |
|---|---|
| `.notNullable()` | `NOT NULL` |
| `.nullable()` | Allows NULL (default) |
| `.defaultTo(value)` | `DEFAULT value` |
| `.defaultTo(knex.fn.now())` | `DEFAULT NOW()` |
| `.defaultTo(knex.raw("'{}'::jsonb"))` | Raw default expression |
| `.unsigned()` | Adds CHECK >= 0 (PG doesn't have native unsigned) |
| `.unique()` | Adds unique constraint |
| `.primary()` | Sets as primary key |
| `.references('id').inTable('other')` | Foreign key |
| `.onDelete('CASCADE')` | FK on delete action |
| `.onUpdate('CASCADE')` | FK on update action |
| `.index()` | Creates a B-tree index |
| `.comment('text')` | Column comment |
| `.alter()` | Alters existing column (in `alterTable`) |
| `.first()` | Column position (MySQL only, ignored in PG) |
| `.after('other')` | Column position (MySQL only, ignored in PG) |

## UUID Primary Keys Pattern

```js
await knex.schema.createTable('resources', (table) => {
  table
    .uuid('id')
    .primary()
    .defaultTo(knex.raw('gen_random_uuid()'));
  // ... other columns
});
```

> `gen_random_uuid()` is available in PostgreSQL 13+. For older versions, enable `pgcrypto`:
> ```sql
> CREATE EXTENSION IF NOT EXISTS "pgcrypto";
> ```
> Then use `knex.raw('gen_random_uuid()')` (pgcrypto also provides this function).

## Composite Primary Keys

```js
await knex.schema.createTable('user_roles', (table) => {
  table.integer('user_id').notNullable().references('id').inTable('users').onDelete('CASCADE');
  table.integer('role_id').notNullable().references('id').inTable('roles').onDelete('CASCADE');
  table.primary(['user_id', 'role_id']);
});
```

## Partial Indexes (via raw SQL)

```js
await knex.raw(`
  CREATE INDEX idx_users_active_email
  ON users (email)
  WHERE is_active = true
`);
```

## GIN Index for JSONB

```js
await knex.raw(`
  CREATE INDEX idx_events_metadata
  ON events USING GIN (metadata)
`);
```

## Full-Text Search Index

```js
await knex.raw(`
  CREATE INDEX idx_articles_search
  ON articles USING GIN (to_tsvector('english', title || ' ' || body))
`);
```
