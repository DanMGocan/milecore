import { useState, useEffect } from 'react';
import { Modal } from './components';

function TableIcon() {
    return (
        <svg className="table-item-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="3" y1="15" x2="21" y2="15"/>
            <line x1="9" y1="3" x2="9" y2="21"/>
        </svg>
    );
}

function CreateTableModal({ open, onClose, onCreated }) {
    const [name, setName] = useState('');
    const [columns, setColumns] = useState([{ name: '', type: 'TEXT' }]);

    const addCol = () => setColumns(prev => [...prev, { name: '', type: 'TEXT' }]);
    const updateCol = (i, field, val) => {
        setColumns(prev => prev.map((c, j) => j === i ? { ...c, [field]: val } : c));
    };
    const removeCol = (i) => setColumns(prev => prev.filter((_, j) => j !== i));

    const submit = async () => {
        const validCols = columns.filter(c => c.name.trim());
        if (!name.trim() || validCols.length === 0) return;
        try {
            const res = await fetch('/api/tables', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim(), columns: validCols }),
            });
            if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
            setName(''); setColumns([{ name: '', type: 'TEXT' }]);
            onCreated();
            onClose();
        } catch (err) { alert(err.message); }
    };

    return (
        <Modal open={open} onClose={onClose} title="Create Table">
            <div className="form-group">
                <label>Table Name</label>
                <input
                    className="form-input" value={name}
                    onChange={e => setName(e.target.value)} placeholder="my_table"
                />
            </div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Columns</label>
            {columns.map((col, i) => (
                <div key={i} className="form-row" style={{ marginTop: 6 }}>
                    <div className="form-group">
                        <input
                            className="form-input" value={col.name}
                            onChange={e => updateCol(i, 'name', e.target.value)} placeholder="column_name"
                        />
                    </div>
                    <div className="form-group" style={{ maxWidth: 120 }}>
                        <select
                            className="form-input" value={col.type}
                            onChange={e => updateCol(i, 'type', e.target.value)}
                        >
                            <option value="TEXT">TEXT</option>
                            <option value="INTEGER">INTEGER</option>
                            <option value="REAL">REAL</option>
                            <option value="BOOLEAN">BOOLEAN</option>
                            <option value="TIMESTAMP">TIMESTAMP</option>
                            <option value="DATE">DATE</option>
                        </select>
                    </div>
                    {columns.length > 1 && (
                        <button
                            className="btn btn-danger btn-sm"
                            onClick={() => removeCol(i)}
                            style={{ marginBottom: 12 }}
                        >
                            &times;
                        </button>
                    )}
                </div>
            ))}
            <button className="btn btn-sm" onClick={addCol} style={{ marginTop: 8 }}>+ Column</button>
            <div className="modal-actions">
                <button className="btn" onClick={onClose}>Cancel</button>
                <button className="btn btn-primary" onClick={submit}>Create</button>
            </div>
        </Modal>
    );
}

function AddColumnModal({ open, onClose, tableName, onAdded }) {
    const [name, setName] = useState('');
    const [type, setType] = useState('TEXT');

    const submit = async () => {
        if (!name.trim()) return;
        try {
            const res = await fetch(`/api/tables/${tableName}/columns`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim(), type }),
            });
            if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
            setName(''); setType('TEXT');
            onAdded();
            onClose();
        } catch (err) { alert(err.message); }
    };

    return (
        <Modal open={open} onClose={onClose} title={`Add Column to ${tableName}`}>
            <div className="form-row">
                <div className="form-group">
                    <label>Column Name</label>
                    <input
                        className="form-input" value={name}
                        onChange={e => setName(e.target.value)} placeholder="column_name"
                    />
                </div>
                <div className="form-group" style={{ maxWidth: 140 }}>
                    <label>Type</label>
                    <select
                        className="form-input" value={type}
                        onChange={e => setType(e.target.value)}
                    >
                        <option value="TEXT">TEXT</option>
                        <option value="INTEGER">INTEGER</option>
                        <option value="REAL">REAL</option>
                        <option value="BOOLEAN">BOOLEAN</option>
                        <option value="TIMESTAMP">TIMESTAMP</option>
                        <option value="DATE">DATE</option>
                    </select>
                </div>
            </div>
            <div className="modal-actions">
                <button className="btn" onClick={onClose}>Cancel</button>
                <button className="btn btn-primary" onClick={submit}>Add</button>
            </div>
        </Modal>
    );
}

function InsertRowModal({ open, onClose, tableName, columns, onInserted }) {
    const editableCols = (columns || []).filter(c => c.name !== 'id' && c.name !== 'rowid');
    const initial = {};
    editableCols.forEach(c => { initial[c.name] = ''; });
    const [data, setData] = useState(initial);

    useEffect(() => {
        const init = {};
        editableCols.forEach(c => { init[c.name] = ''; });
        setData(init);
    }, [tableName, open]);

    const submit = async () => {
        const filtered = {};
        Object.entries(data).forEach(([k, v]) => { if (v !== '') filtered[k] = v; });
        if (Object.keys(filtered).length === 0) return;
        try {
            const res = await fetch(`/api/tables/${tableName}/rows`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: filtered }),
            });
            if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
            onInserted();
            onClose();
        } catch (err) { alert(err.message); }
    };

    return (
        <Modal open={open} onClose={onClose} title={`Insert Row into ${tableName}`}>
            {editableCols.map(col => (
                <div key={col.name} className="form-group">
                    <label>{col.name} ({col.type})</label>
                    <input
                        className="form-input"
                        value={data[col.name] || ''}
                        onChange={e => setData(prev => ({ ...prev, [col.name]: e.target.value }))}
                        placeholder={col.default_value ? `Default: ${col.default_value}` : ''}
                    />
                </div>
            ))}
            <div className="modal-actions">
                <button className="btn" onClick={onClose}>Cancel</button>
                <button className="btn btn-primary" onClick={submit}>Insert</button>
            </div>
        </Modal>
    );
}

export function BrowserPage() {
    const [tables, setTables] = useState([]);
    const [selected, setSelected] = useState(null);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [schema, setSchema] = useState([]);
    const [rows, setRows] = useState([]);
    const [columns, setColumns] = useState([]);
    const [total, setTotal] = useState(0);
    const [offset, setOffset] = useState(0);
    const limit = 50;

    const [showCreate, setShowCreate] = useState(false);
    const [showAddCol, setShowAddCol] = useState(false);
    const [showInsert, setShowInsert] = useState(false);

    const loadTables = async () => {
        try {
            const res = await fetch('/api/tables');
            const data = await res.json();
            setTables(data.tables || []);
        } catch (err) { console.error(err); }
    };

    const loadTable = async (name, newOffset) => {
        const off = newOffset !== undefined ? newOffset : 0;
        try {
            const [schemaRes, rowsRes] = await Promise.all([
                fetch(`/api/tables/${name}/schema`),
                fetch(`/api/tables/${name}/rows?limit=${limit}&offset=${off}`),
            ]);
            const schemaData = await schemaRes.json();
            const rowsData = await rowsRes.json();
            setSchema(schemaData.columns || []);
            setColumns(rowsData.columns || []);
            setRows(rowsData.rows || []);
            setTotal(rowsData.total || 0);
            setOffset(off);
        } catch (err) { console.error(err); }
    };

    const selectTable = (name) => {
        setSelected(name);
        loadTable(name, 0);
        setSidebarOpen(false);
    };

    const deleteRow = async (rowId) => {
        if (!confirm('Delete this row?')) return;
        try {
            const res = await fetch(`/api/tables/${selected}/rows/${rowId}`, { method: 'DELETE' });
            if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
            loadTable(selected, offset);
        } catch (err) { alert(err.message); }
    };

    const dropTable = async () => {
        if (!confirm(`Drop table "${selected}"? This cannot be undone.`)) return;
        try {
            const res = await fetch(`/api/tables/${selected}`, { method: 'DELETE' });
            if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
            setSelected(null);
            setSchema([]); setRows([]); setColumns([]);
            loadTables();
        } catch (err) { alert(err.message); }
    };

    useEffect(() => { loadTables(); }, []);

    const totalPages = Math.ceil(total / limit);
    const currentPage = Math.floor(offset / limit) + 1;

    return (
        <div className="browser-container">
            {/* Sidebar */}
            <div className={`sidebar-backdrop${sidebarOpen ? ' visible' : ''}`} onClick={() => setSidebarOpen(false)} />
            <button className="sidebar-toggle-btn browser-sidebar-toggle" onClick={() => setSidebarOpen(o => !o)} aria-label="Toggle sidebar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/>
                </svg>
            </button>
            <div className={`browser-sidebar${sidebarOpen ? ' open' : ''}`}>
                <div className="sidebar-header">
                    <h3>Tables</h3>
                    <button className="btn btn-sm btn-primary" onClick={() => setShowCreate(true)}>+ New</button>
                </div>
                <div className="sidebar-list">
                    {tables.map(t => (
                        <div
                            key={t}
                            className={`table-item${selected === t ? ' active' : ''}`}
                            onClick={() => selectTable(t)}
                        >
                            <TableIcon />
                            <span className="table-item-name">{t}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Main content */}
            <div className="browser-main">
                {selected ? (
                    <>
                        {/* Schema section */}
                        <div className="schema-section">
                            <h4>Schema</h4>
                            <div className="schema-grid">
                                {schema.map(col => (
                                    <div key={col.name} className="schema-col">
                                        {col.pk && <span className="schema-col-pk">PK</span>}
                                        <span className="schema-col-name">{col.name}</span>
                                        <span className="schema-col-type">{col.type}</span>
                                        {col.notnull && <span className="schema-col-nn">NN</span>}
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Toolbar */}
                        <div className="browser-toolbar">
                            <h2>{selected}{' '}
                                <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 400 }}>({total} rows)</span>
                            </h2>
                            <div className="toolbar-actions">
                                <button className="btn btn-sm" onClick={() => setShowInsert(true)}>+ Row</button>
                                <button className="btn btn-sm" onClick={() => setShowAddCol(true)}>+ Column</button>
                                <button className="btn btn-sm" onClick={() => loadTable(selected, offset)}>Refresh</button>
                                <button className="btn btn-sm btn-danger" onClick={dropTable}>Drop</button>
                            </div>
                        </div>

                        {/* Data grid */}
                        <div className="browser-content browser-content-fade" key={selected + '-' + offset}>
                            {rows.length > 0 ? (
                                <div className="data-grid-scroll-wrapper">
                                <table className="data-grid">
                                    <thead>
                                        <tr>
                                            {columns.map(c => <th key={c}>{c}</th>)}
                                            <th scope="col">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows.map((row, i) => (
                                            <tr key={i}>
                                                {columns.map(c => (
                                                    <td key={c} title={row[c] != null ? String(row[c]) : ''}>
                                                        {row[c] != null ? String(row[c]) : ''}
                                                    </td>
                                                ))}
                                                <td>
                                                    <button
                                                        className="delete-row-btn"
                                                        onClick={() => deleteRow(row.rowid || row.id)}
                                                        aria-label={`Delete row ${row.rowid || row.id}`}
                                                    >
                                                        Del
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                </div>
                            ) : (
                                <div className="browser-empty-state">
                                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.3 }}>
                                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                        <line x1="3" y1="9" x2="21" y2="9"/>
                                        <line x1="9" y1="3" x2="9" y2="21"/>
                                    </svg>
                                    <div>No rows in this table</div>
                                </div>
                            )}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="pagination">
                                <button
                                    className="btn btn-sm"
                                    disabled={currentPage <= 1}
                                    onClick={() => loadTable(selected, offset - limit)}
                                >
                                    Prev
                                </button>
                                <span>Page <span className="page-indicator">{currentPage}</span> of {totalPages}</span>
                                <button
                                    className="btn btn-sm"
                                    disabled={currentPage >= totalPages}
                                    onClick={() => loadTable(selected, offset + limit)}
                                >
                                    Next
                                </button>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="browser-empty-state browser-empty-state--full">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.3 }}>
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                        </svg>
                        <div>Select a table to browse</div>
                    </div>
                )}
            </div>

            {/* Modals */}
            <CreateTableModal
                open={showCreate} onClose={() => setShowCreate(false)}
                onCreated={() => { loadTables(); }}
            />
            {selected && (
                <AddColumnModal
                    open={showAddCol} onClose={() => setShowAddCol(false)}
                    tableName={selected} onAdded={() => loadTable(selected, offset)}
                />
            )}
            {selected && (
                <InsertRowModal
                    open={showInsert} onClose={() => setShowInsert(false)}
                    tableName={selected} columns={schema} onInserted={() => loadTable(selected, offset)}
                />
            )}
        </div>
    );
}
