#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TanStack Skill - React ecosystem completo
Uso: Generar código para TanStack Query, Router, Table, Store
"""
import json

class TanStackSkill:
    def __init__(self):
        self.name = "TanStackSkill"
        self.libs = ["query", "router", "table", "store", "form", "virtual"]
    
    def install(self, lib: str = "all") -> str:
        """Genera comando de instalación"""
        if lib == "all":
            return "npm install @tanstack/react-query @tanstack/react-router @tanstack/react-table @tanstack/react-store @tanstack/react-form"
        if lib not in self.libs:
            return f"[ERROR] Lib debe ser: {', '.join(self.libs)} o 'all'"
        return f"npm install @tanstack/react-{lib}"
    
    def generate_query(self, query_key: str, endpoint: str) -> str:
        """Genera código para TanStack Query"""
        code = f"""import {{ useQuery }} from '@tanstack/react-query';

export function use{query_key}() {{
  return useQuery({{
    queryKey: ['{query_key.lower()}'],
    queryFn: async () => {{
      const res = await fetch('{endpoint}');
      if (!res.ok) throw new Error('Error fetching');
      return res.json();
    }},
  }};
}}
"""
        return f"[CODE]\n{code}"
    
    def generate_router(self, routes: list) -> str:
        """Genera configuración de TanStack Router"""
        routes_str = ",\n".join([
            f"    {{ path: '{r['path']}', component: {r['component']} }}"
            for r in routes
        ])
        code = f"""import {{ createRouter, RouterProvider }} from '@tanstack/react-router';
import {{ Root, NotFound }} from './components';

const router = createRouter({{
  rootComponent: Root,
  notFoundComponent: NotFound,
  routes: [
{routes_str}
  ],
}});

export function App() {{
  return <RouterProvider router={{router}} />;
}}
"""
        return f"[CODE]\n{code}"
    
    def generate_table(self, columns: list, data_var: str = "data") -> str:
        """Genera tabla con TanStack Table"""
        cols_str = ",\n".join([
            f"    {{ accessorKey: '{c}', header: '{c.title()}' }}"
            for c in columns
        ])
        code = f"""import {{
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
}} from '@tanstack/react-table';

const columns = [
{cols_str}
];

function Table() {{
  const table = useReactTable({{
    data: {data_var},
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  }});

  return (
    <table>
      <thead>
        {{table.getHeaderGroups().map(headerGroup => (
          <tr key={{headerGroup.id}}>
            {{headerGroup.headers.map(header => (
              <th key={{header.id}}>
                {{flexRender(header.column.columnDef.header, header.getContext())}}
              </th>
            ))}}
          </tr>
        ))}}
      </thead>
      <tbody>
        {{table.getRowModel().rows.map(row => (
          <tr key={{row.id}}>
            {{row.getVisibleCells().map(cell => (
              <td key={{cell.id}}>
                {{flexRender(cell.column.columnDef.cell, cell.getContext())}}
              </td>
            ))}}
          </tr>
        ))}}
      </tbody>
    </table>
  );
}}
"""
        return f"[CODE]\n{code}"
    
    def generate_store(self, store_name: str, initial_state: dict) -> str:
        """Genera store con TanStack Store"""
        state_str = json.dumps(initial_state, indent=4)
        code = f"""import {{ createStore }} from '@tanstack/react-store';

export const {store_name}Store = createStore({{
  state: {state_str},
  actions: {{
    update(prevState, payload) {{
      return {{ ...prevState, ...payload }};
    }},
  }},
}});
"""
        return f"[CODE]\n{code}"
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": "React ecosystem: Query, Router, Table, Store, Form",
            "install": self.install("all"),
            "docs": "https://tanstack.com"
        }

if __name__ == "__main__":
    skill = TanStackSkill()
    print(json.dumps(skill.info(), indent=2))
