import { useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight, Columns3, Search } from "lucide-react";

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T, unknown>[];
  pageSize?: number;
  searchable?: boolean;
  selectable?: boolean;
  serverPagination?: {
    pageIndex: number;
    pageCount: number;
    onPageChange: (page: number) => void;
  };
  onRowClick?: (row: T) => void;
  selectedRows?: RowSelectionState;
  onSelectionChange?: (selection: RowSelectionState) => void;
}

export default function DataTable<T>({
  data,
  columns,
  pageSize = 25,
  searchable = true,
  selectable = false,
  serverPagination,
  onRowClick,
  selectedRows,
  onSelectionChange,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnVisibility, setColumnVisibility] = useState({});
  const [colMenuOpen, setColMenuOpen] = useState(false);
  const [internalSelection, setInternalSelection] = useState<RowSelectionState>({});

  const rowSelection = selectedRows ?? internalSelection;
  const setRowSelection = (onSelectionChange ?? setInternalSelection) as (updater: RowSelectionState | ((old: RowSelectionState) => RowSelectionState)) => void;

  const allColumns: ColumnDef<T, unknown>[] = selectable
    ? [
        {
          id: "select",
          header: ({ table }) => (
            <input
              type="checkbox"
              className="accent-primary"
              checked={table.getIsAllPageRowsSelected()}
              onChange={table.getToggleAllPageRowsSelectedHandler()}
            />
          ),
          cell: ({ row }) => (
            <input
              type="checkbox"
              className="accent-primary"
              checked={row.getIsSelected()}
              onChange={row.getToggleSelectedHandler()}
              onClick={(e) => e.stopPropagation()}
            />
          ),
          size: 40,
          enableSorting: false,
        },
        ...columns,
      ]
    : columns;

  const table = useReactTable({
    data,
    columns: allColumns,
    state: { sorting, globalFilter, columnVisibility, rowSelection },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: serverPagination ? undefined : getPaginationRowModel(),
    enableRowSelection: selectable,
    initialState: { pagination: { pageSize } },
  });

  const pageIndex = serverPagination?.pageIndex ?? table.getState().pagination.pageIndex;
  const pageCount = serverPagination?.pageCount ?? table.getPageCount();

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2">
        {searchable && (
          <div className="relative flex-1">
            <Search className="absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder="Search..."
              className="w-full rounded-lg border border-dark-border bg-dark-card ps-9 pe-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-primary/50 focus:outline-none"
            />
          </div>
        )}
        <div className="relative">
          <button
            onClick={() => setColMenuOpen(!colMenuOpen)}
            className="flex items-center gap-1.5 rounded-lg border border-dark-border px-3 py-2 text-sm text-slate-400 hover:bg-white/5"
          >
            <Columns3 className="h-4 w-4" />
          </button>
          {colMenuOpen && (
            <div className="absolute end-0 top-full z-50 mt-1 w-48 rounded-lg glass-card border border-dark-border py-1 shadow-xl">
              {table.getAllLeafColumns().filter((c) => c.id !== "select").map((col) => (
                <label key={col.id} className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5">
                  <input
                    type="checkbox"
                    className="accent-primary"
                    checked={col.getIsVisible()}
                    onChange={col.getToggleVisibilityHandler()}
                  />
                  {typeof col.columnDef.header === "string" ? col.columnDef.header : col.id}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-dark-border">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-dark-border bg-dark-card/50">
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
                    className={`px-4 py-3 text-start text-xs font-medium uppercase tracking-wider text-slate-500 ${header.column.getCanSort() ? "cursor-pointer select-none hover:text-slate-300" : ""}`}
                    style={{ width: header.getSize() !== 150 ? header.getSize() : undefined }}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        header.column.getIsSorted() === "asc" ? <ChevronUp className="h-3 w-3" />
                        : header.column.getIsSorted() === "desc" ? <ChevronDown className="h-3 w-3" />
                        : <ChevronsUpDown className="h-3 w-3 opacity-30" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                onClick={() => onRowClick?.(row.original)}
                className={`border-b border-dark-border/50 transition-colors ${onRowClick ? "cursor-pointer" : ""} ${row.getIsSelected() ? "bg-primary/5" : "hover:bg-white/[0.02]"}`}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3 text-slate-300">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td colSpan={allColumns.length} className="px-4 py-12 text-center text-slate-600">
                  No data found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-500">
          {selectable && Object.keys(rowSelection).length > 0
            ? `${Object.keys(rowSelection).length} of ${data.length} selected`
            : `${data.length} records`}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => serverPagination ? serverPagination.onPageChange(pageIndex - 1) : table.previousPage()}
            disabled={serverPagination ? pageIndex <= 0 : !table.getCanPreviousPage()}
            className="rounded-lg border border-dark-border p-1.5 text-slate-400 hover:bg-white/5 disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-slate-400">
            {pageIndex + 1} / {pageCount || 1}
          </span>
          <button
            onClick={() => serverPagination ? serverPagination.onPageChange(pageIndex + 1) : table.nextPage()}
            disabled={serverPagination ? pageIndex >= pageCount - 1 : !table.getCanNextPage()}
            className="rounded-lg border border-dark-border p-1.5 text-slate-400 hover:bg-white/5 disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
