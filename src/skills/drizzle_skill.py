#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Drizzle Skill - TypeScript ORM moderno y rápido
Uso: Generar esquemas, migraciones y consultas con Drizzle ORM
"""
import json
import os

class DrizzleSkill:
    def __init__(self):
        self.name = "DrizzleSkill"
    
    def generate_schema(self, tables: dict, output_path: str = "db/schema.ts") -> str:
        """Genera un archivo de esquema Drizzle"""
        lines = [
            'import { pgTable, serial, text, varchar, integer, boolean, timestamp, pgEnum } from "drizzle-orm/pg-core";',
            'import { relations } from "drizzle-orm";',
            '',
        ]
        
        for table_name, columns in tables.items():
            lines.append(f"// Tabla: {table_name}")
            # Generate pgTable definition
            lines.append(f"export const {table_name} = pgTable('{table_name}', {{")
            for col_name, col_type in columns.items():
                drizzle_type = self._map_type(col_type)
                lines.append(f"  {col_name}: {drizzle_type},")
            lines.append("});")
            lines.append("")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
        return f"[OK] Schema guardado en {output_path}"
    
    def _map_type(self, col_type: str) -> str:
        """Mapea tipos a Drizzle"""
        type_map = {
            "serial": "serial('id').primaryKey()",
            "int": "integer('{col_name}')",
            "string": "varchar('{col_name}', 255)",
            "text": "text('{col_name}')",
            "boolean": "boolean('{col_name}')",
            "timestamp": "timestamp('{col_name}').defaultNow()",
        }
        return type_map.get(col_type, f"varchar('{col_name}', 255)")
    
    def generate_migration(self, schema_path: str = "db/schema.ts") -> str:
        """Genera comando para migración"""
        return f"[INFO] Ejecuta: npx drizzle-kit generate:pg --schema={schema_path}"
    
    def generate_config(self, output_path: str = "drizzle.config.ts") -> str:
        """Genera drizzle.config.ts"""
        config = """import type { Config } from "drizzle-kit";

export default {
  schema: "./db/schema.ts",
  out: "./drizzle",
  driver: "pg",
  dbCredentials: {
    connectionString: process.env.DATABASE_URL!,
  },
} satisfies Config;
"""
        with open(output_path, "w") as f:
            f.write(config)
        return f"[OK] drizzle.config.ts creado en {output_path}"
    
    def example_crud(self, table_name: str) -> str:
        """Genera ejemplo CRUD con Drizzle"""
        code = f"""// CRUD ejemplo para {table_name}
import {{ db }} from './db';
import {{ {table_name} }} from './schema';

// Create
const newItem = await db.insert({table_name}).values({{
  // ... campos
}}).returning();

// Read
const items = await db.select().from({table_name});

// Update
await db.update({table_name})
  .set({{ /* campos */ }})
  .where(eq({table_name}.id, id));

// Delete
await db.delete({table_name}).where(eq({table_name}.id, id));
"""
        return f"[CODE]\n{code}"
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": "TypeScript ORM rápido y type-safe",
            "install": "npm install drizzle-orm pg && npm install -D drizzle-kit",
            "docs": "https://orm.drizzle.team"
        }

if __name__ == "__main__":
    skill = DrizzleSkill()
    print(json.dumps(skill.info(), indent=2))
