# Common Migration Patterns

## Pattern: Add a Column with Backfill (Zero-Downtime)

When you need to add a NOT NULL column to a large production table without downtime:

### Step 1 — Migration: Add column as nullable

```js
// 20240101120000_add_slug_to_posts.js
exports.up = async function (knex) {
  await knex.schema.alterTable('posts', (table) => {
    table.string('slug', 255); // nullable first
    table.index('slug', 'idx_posts_slug');
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('posts', (table) => {
    table.dropIndex('slug', 'idx_posts_slug');
    table.dropColumn('slug');
  });
};
```

### Step 2 — Deploy code that writes to the new column

### Step 3 — Migration: Backfill existing rows

```js
// 20240102120000_backfill_posts_slug.js
exports.up = async function (knex) {
  const BATCH = 1000;
  let count;
  do {
    const result = await knex.raw(`
      UPDATE posts
      SET slug = LOWER(REPLACE(title, ' ', '-'))
      WHERE id IN (
        SELECT id FROM posts WHERE slug IS NULL LIMIT ?
      )
    `, [BATCH]);
    count = result.rowCount;
  } while (count > 0);
};

exports.down = async function (knex) {
  await knex('posts').update({ slug: null });
};
```

### Step 4 — Migration: Make column NOT NULL

```js
// 20240103120000_make_posts_slug_not_null.js
exports.up = async function (knex) {
  await knex.schema.alterTable('posts', (table) => {
    table.string('slug', 255).notNullable().alter();
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('posts', (table) => {
    table.string('slug', 255).nullable().alter();
  });
};
```

---

## Pattern: Rename a Table

```js
exports.up = async function (knex) {
  await knex.schema.renameTable('posts', 'articles');
};

exports.down = async function (knex) {
  await knex.schema.renameTable('articles', 'posts');
};
```

---

## Pattern: Many-to-Many Join Table

```js
exports.up = async function (knex) {
  await knex.schema.createTable('post_tags', (table) => {
    table.integer('post_id').unsigned().notNullable()
      .references('id').inTable('posts').onDelete('CASCADE');
    table.integer('tag_id').unsigned().notNullable()
      .references('id').inTable('tags').onDelete('CASCADE');
    table.primary(['post_id', 'tag_id']);
    table.index('tag_id', 'idx_post_tags_tag_id');
    table.timestamp('created_at').notNullable().defaultTo(knex.fn.now());
  });
};

exports.down = async function (knex) {
  await knex.schema.dropTableIfExists('post_tags');
};
```

---

## Pattern: Polymorphic Association

```js
exports.up = async function (knex) {
  await knex.schema.createTable('comments', (table) => {
    table.increments('id').primary();
    table.string('commentable_type', 50).notNullable(); // 'post', 'video', etc.
    table.integer('commentable_id').notNullable();
    table.text('body').notNullable();
    table.integer('user_id').unsigned().notNullable()
      .references('id').inTable('users').onDelete('CASCADE');
    table.timestamps(true, true);

    table.index(
      ['commentable_type', 'commentable_id'],
      'idx_comments_commentable'
    );
  });
};

exports.down = async function (knex) {
  await knex.schema.dropTableIfExists('comments');
};
```

---

## Pattern: Soft Delete

```js
exports.up = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.timestamp('deleted_at').nullable();
    table.index('deleted_at', 'idx_users_deleted_at');
  });
};

exports.down = async function (knex) {
  await knex.schema.alterTable('users', (table) => {
    table.dropIndex('deleted_at', 'idx_users_deleted_at');
    table.dropColumn('deleted_at');
  });
};
```

---

## Pattern: Add CHECK Constraint

```js
exports.up = async function (knex) {
  await knex.raw(`
    ALTER TABLE products
    ADD CONSTRAINT chk_products_price_positive CHECK (price >= 0)
  `);
};

exports.down = async function (knex) {
  await knex.raw(`
    ALTER TABLE products
    DROP CONSTRAINT IF EXISTS chk_products_price_positive
  `);
};
```

---

## Pattern: Create a View

```js
exports.up = async function (knex) {
  await knex.raw(`
    CREATE OR REPLACE VIEW active_users AS
    SELECT id, email, name, created_at
    FROM users
    WHERE is_active = true AND deleted_at IS NULL
  `);
};

exports.down = async function (knex) {
  await knex.raw('DROP VIEW IF EXISTS active_users');
};
```

---

## Pattern: Add a Trigger (e.g., auto-update `updated_at`)

```js
exports.up = async function (knex) {
  // Create the function (idempotent)
  await knex.raw(`
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
  `);

  // Attach trigger
  await knex.raw(`
    CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
  `);
};

exports.down = async function (knex) {
  await knex.raw('DROP TRIGGER IF EXISTS trg_users_updated_at ON users');
  // Optionally drop the function if no other triggers use it
  // await knex.raw('DROP FUNCTION IF EXISTS update_updated_at_column');
};
```

---

## Pattern: Enable an Extension

```js
exports.up = async function (knex) {
  await knex.raw('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"');
};

exports.down = async function (knex) {
  await knex.raw('DROP EXTENSION IF EXISTS "uuid-ossp"');
};
```
