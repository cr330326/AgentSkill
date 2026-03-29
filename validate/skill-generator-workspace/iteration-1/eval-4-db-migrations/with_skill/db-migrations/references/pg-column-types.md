# PostgreSQL Column Types → Knex Schema Builder

Quick reference for mapping PostgreSQL types to Knex table builder methods.

## Numeric

| PostgreSQL type | Knex method | Notes |
|----------------|-------------|-------|
| `serial` / `integer` + auto-increment | `table.increments('id')` | Creates `id serial PRIMARY KEY` |
| `bigserial` | `table.bigIncrements('id')` | 64-bit auto-increment |
| `integer` | `table.integer('col')` | 32-bit signed |
| `bigint` | `table.bigInteger('col')` | 64-bit signed |
| `smallint` | `table.smallint('col')` | 16-bit signed |
| `decimal(p,s)` / `numeric(p,s)` | `table.decimal('col', precision, scale)` | Exact numeric |
| `real` | `table.float('col', 4)` | 32-bit float |
| `double precision` | `table.float('col', 8)` | 64-bit float |

## String / Text

| PostgreSQL type | Knex method | Notes |
|----------------|-------------|-------|
| `varchar(n)` | `table.string('col', n)` | Default n=255 if omitted |
| `text` | `table.text('col')` | Unlimited length |
| `char(n)` | `table.specificType('col', 'char(n)')` | Fixed-length |

## Date / Time

| PostgreSQL type | Knex method | Notes |
|----------------|-------------|-------|
| `timestamp` | `table.timestamp('col')` | Without timezone |
| `timestamptz` | `table.timestamp('col', { useTz: true })` | With timezone (preferred) |
| `created_at` + `updated_at` | `table.timestamps(true, true)` | Both as `timestamptz`, with defaults |
| `date` | `table.date('col')` | Date only |
| `time` | `table.time('col')` | Time only |

## Boolean / Binary

| PostgreSQL type | Knex method | Notes |
|----------------|-------------|-------|
| `boolean` | `table.boolean('col')` | |
| `bytea` | `table.binary('col')` | Binary data |

## JSON

| PostgreSQL type | Knex method | Notes |
|----------------|-------------|-------|
| `json` | `table.json('col')` | Stored as text, validated on input |
| `jsonb` | `table.jsonb('col')` | Binary JSON, supports indexing and operators |

## UUID

| PostgreSQL type | Knex method | Notes |
|----------------|-------------|-------|
| `uuid` | `table.uuid('col')` | Needs `pgcrypto` or `uuid-ossp` for `gen_random_uuid()` |

Use with default:
```js
table.uuid('id').primary().defaultTo(knex.raw('gen_random_uuid()'));
```

Ensure extension is enabled:
```js
await knex.raw('CREATE EXTENSION IF NOT EXISTS "pgcrypto"');
```

## Enum

PostgreSQL native enums require raw SQL:

```js
// Create the type
await knex.raw(`CREATE TYPE status_type AS ENUM ('active', 'inactive', 'archived')`);

// Use it in a table
table.specificType('status', 'status_type').defaultTo('active');
```

Knex also supports `table.enu('col', ['a', 'b'])` which creates a CHECK constraint
(not a native PG enum type). Prefer native enums for shared types.

## Array

```js
table.specificType('tags', 'text[]');
table.specificType('scores', 'integer[]');
```

## Column Modifiers

| Modifier | Knex method |
|----------|-------------|
| NOT NULL | `.notNullable()` |
| NULLABLE | `.nullable()` |
| DEFAULT value | `.defaultTo(value)` |
| PRIMARY KEY | `.primary()` |
| UNIQUE | `.unique()` |
| REFERENCES | `.references('id').inTable('other_table')` |
| ON DELETE CASCADE | `.onDelete('CASCADE')` |
| ON UPDATE CASCADE | `.onUpdate('CASCADE')` |
| INDEX | `.index()` or `table.index('col')` |
| COMMENT | `.comment('description')` |
